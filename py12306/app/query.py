import asyncio
import copy
import datetime
import random
import re
from typing import List, Optional

from app.app import Event, Cache, Notification
from app.app import Logger, Config
from app.models import QueryJob, Ticket
from lib.exceptions import RetryException
from lib.hammer import EventItem
from lib.helper import TrainSeat, TaskManager, number_of_time_period, retry
from lib.request import TrainSession


class QueryTicketManager(TaskManager):

    async def run(self):
        Logger.info('正在加载查询任务...')
        while True:
            await self.make_tasks()
            self.clean_fuatures()
            await asyncio.sleep(self.interval)

    @property
    async def task_total(self):
        return await QueryJob.filter_available().count()

    async def make_tasks(self):
        if await self.is_overflow:  # 丢弃多余任务
            self.tasks.popitem()
        for query_job in await QueryJob.all():
            if self.get_task(query_job.id):
                if not query_job.is_available:
                    self.stop_and_drop(query_job.id)
                    Logger.debug(f'任务 {query_job.name_text} 不可用，已停止该任务')
                continue
            if query_job.status == query_job.Status.WaitVerify or not query_job.passengers:  # 乘客验证
                Logger.debug(f'验证任务 {query_job.name_text} 乘客信息...')
                if not query_job.user_id:
                    query_job.status = query_job.Status.Normal
                    await query_job.save()
                else:
                    await Event.publish(
                        EventItem(Event.EVENT_VERIFY_QUERY_JOB, {'id': query_job.id, 'user_id': query_job.user_id}))
                continue
            if await self.is_full:
                continue
            if Config.redis_able and query_job.is_alive:
                Logger.debug(f'任务 {query_job.name_text} 正在运行中，已跳过')
                continue
            await self.handle_task(query_job)

    async def handle_task(self, query: QueryJob):
        """ 添加查询任务 """
        if not query.is_queryable:
            Logger.debug(f'任务 {query.name_text} 未满足查询条件，已跳过')
            return False
        ticket = QueryTicket(query)
        Logger.info(f'# 查询任务 [{query.route_time_text}] 已添加到任务中 #')
        self.add_task(ticket.run(), query.id, ticket)


class QueryTicket:
    """ 车票查询 """

    def __init__(self, query: QueryJob):
        self.api_type: str = ''
        self.session = TrainSession(use_proxy=True, timeout=5)
        self.query: QueryJob = query
        self._last_process_at = query.last_process_at
        self._last_notifaction_at: Optional[datetime] = None
        self._is_stop = False
        self.__flag_num: int = 0  # 连续查询失败次数

    @retry()
    async def get_query_api_type(self) -> str:
        """ 动态获取查询的接口， 如 leftTicket/query """
        if self.api_type:
            return self.api_type
        response = await self.session.otn_left_ticket_init()
        if response.status == 200:
            res = re.search(r'var CLeftTicketUrl = \'(.*)\';', response.text())
            try:
                self.api_type = res.group(1)
                Logger.info(f'更新查询接口地址: {self.api_type}')
            except (IndexError, AttributeError):
                raise RetryException('获取车票查询地址失败')
        return await self.get_query_api_type()

    async def run(self):
        """
        ) 更新查询接口地址
        ) 查询可用的 ticket
        ) """
        await self.get_query_api_type()
        while self.is_runable:
            await self.query.refresh_from_db()
            # 检测同时运行可能导致任务重复
            if self.query.last_process_at != self._last_process_at:
                break
            self._last_process_at = await self.query.update_last_process_at()
            fuatures = []
            try:
                for _ in range(0, Config.get('proxy.concurrent_num', 1) if Config.proxy_able else 1):
                    fuatures.append(asyncio.ensure_future(self.query_tickets()))
                await asyncio.wait(fuatures)
                # await self.query_tickets()
            except Exception as e:
                Logger.error(f'查询错误 {e}')
            finally:
                await self.query.save()
            # 下单  TODO
            # await asyncio.sleep(5)
            if Config.IS_IN_TEST:
                break

    async def query_tickets(self):
        """ 余票查询 """
        query_num = self.query.query_num_next
        query = copy.deepcopy(self.query)
        Logger.info('')
        Logger.info(f">> 第 {query_num} 次查询 {query.route_text.replace('-', '👉')} {datetime.datetime.now()}")
        for left_date in query.left_dates:
            query.left_date = left_date
            if not query.current_is_queryable:
                continue
            for station in query.stations:
                query.left_station, query.arrive_station = station
                tickets, stay_interval = await self.get_available_tickets(query)
                for ticket in tickets:
                    # 验证完成，准备下单
                    Logger.info(
                        f"[ 查询到座位可用 出发时间 {query.left_date} 车次 {ticket.train_number} 座位类型 {ticket.available_seat.get('name')} 余票数量 {ticket.ticket_num} ]")
                    if not Config.IS_IN_TEST:
                        await self._make_order_happen(query, ticket)
                await asyncio.sleep(stay_interval)

    @retry()
    async def get_available_tickets(self, query: QueryJob):
        """ 查询余票 """
        available_tickets = []
        output_train_nums = []
        tickets = await self.get_tickets_from_query(query)
        for ticket in tickets:
            if self.verify_train_number(ticket, query):
                output_train_nums.append(ticket.train_number)
            if not self.is_ticket_valid(ticket):
                continue
            available_tickets.append(ticket)
        tabs = '\t'
        stay_interval = self.get_query_interval(len(tickets) > 0)
        output_train_nums = output_train_nums or ['无可下单车次']
        Logger.info(
            f"出发日期 {query.left_date}: {query.left_station} - {query.arrive_station} {tabs} 车次 "
            f"{tabs.join(output_train_nums)} {tabs} 停留 {stay_interval:.2f}")
        return available_tickets, stay_interval

    @retry
    async def get_tickets_from_query(self, query: QueryJob) -> List[Ticket]:
        response = await self.session.otn_query_left_ticket(await self.get_query_api_type(), query)
        if response.status is not 200:
            Logger.error(f'车票查询失败, 状态码 {response.status}, {response.reason} 请求被拒绝')
            raise RetryException(wait_s=1, default=[])
        result = response.json().get('data.result')
        if not result:
            Logger.error(f'车票查询失败, {response.reason}')
            return []
        return Ticket.parse_tickets_text(result)

    def is_ticket_valid(self, ticket: Ticket) -> bool:
        """
        验证 Ticket 信息是否可用
        ) 出发日期验证
        ) 车票数量验证
        ) 时间点验证(00:00 - 24:00)
        ) 车次验证
        ) 座位验证
        ) 乘车人数验证
        :param ticket: 车票信息
        :param query:  查询条件
        :return:
        """
        if not self.verify_ticket_num(ticket):
            return False

        if not self.verify_period(ticket.left_time, self.query.left_periods):
            return False

        if not self.verify_train_number(ticket, self.query):
            return False

        if not self.verify_seat(ticket, self.query):
            return False
        if not self.verify_member_count(ticket, self.query):
            return False

        return True

    @staticmethod
    def verify_period(period: str, available_periods: List[str]):
        """ 时间点验证(00:00 - 24:00) """
        if not available_periods:
            return True
        period = number_of_time_period(period)
        if period < number_of_time_period(available_periods[0]) or \
                period > number_of_time_period(available_periods[1]):
            return False
        return True

    @staticmethod
    def verify_ticket_num(ticket: Ticket):
        """ 车票数量验证 """
        return ticket.ticket_num == 'Y' and ticket.order_text == '预订'

    @classmethod
    def verify_seat(cls, ticket: Ticket, query: QueryJob) -> bool:
        """ 检查座位是否可用
        TODO 小黑屋判断   通过 车次 + 座位
        """
        allow_seats = query.allow_seats
        for seat in allow_seats:
            seat_id = TrainSeat.ticket_id[seat]
            raw = ticket.raw[seat_id]
            if cls.verify_seat_text(raw):
                # TODO order model
                ticket.available_seat = {
                    'name': seat,
                    'id': seat_id,
                    'raw': raw,
                    'order_id': TrainSeat.order_id[seat]
                }
                return True
        return False

    @staticmethod
    def verify_seat_text(seat: str) -> bool:
        return seat != '' and seat != '无' and seat != '*'

    @staticmethod
    def verify_member_count(ticket: Ticket, query: QueryJob) -> bool:
        """ 乘车人数验证 """
        # TODO 多座位类型判断
        ticket.member_num_take = query.member_num
        seat_raw = ticket.available_seat.get('raw', '')
        if not (seat_raw == '有' or query.member_num <= int(seat_raw)):
            rest_num = int(seat_raw)
            if query.less_member:
                ticket.member_num_take = rest_num
                Logger.info(f'余票数小于乘车人数，当前余票数: {rest_num}, 实际人数 {query.member_num}, 删减人车人数到: {ticket.member_num_take}')
            else:
                Logger.info(f'余票数 {rest_num} 小于乘车人数 {query.member_num}，放弃此次提交机会')
                return False
        return True

    @staticmethod
    def verify_train_number(ticket: Ticket, query: QueryJob) -> bool:
        """ 车次验证 """
        if query.allow_train_numbers and ticket.train_number not in query.allow_train_numbers:
            return False
        if query.execpt_train_numbers and ticket.train_number in query.execpt_train_numbers:
            return False
        return True

    def get_query_interval(self, flag: bool = True):
        """ 获取查询等待间隔，代理开启时无需等待  """
        if Config.proxy_able:
            return 0
        if flag:
            self.__flag_num = 0
        interval = Config.get('query_interval', 1)
        rand = random.randint(1, 10) * 0.05
        self.__flag_num += 1
        return round(interval + rand + self.__flag_num * 0.5, 2)

    async def _make_order_happen(self, query: QueryJob, ticket: Ticket):
        """ 生成下单事件 """
        if await Cache.in_dark_room(ticket.baby):
            Logger.info(f'{ticket.train_number} 已关进小黑屋，跳过本次下单')
            return
        if query.user_id:
            # 这里尽量减少网络传输数据大小，只传递必要数据
            await Event.publish(EventItem(Event.EVENT_ORDER_TICKET, {
                'user_id': query.user_id,
                'query_job': {
                    'hash_id': query.hash_id,
                    'left_date': query.left_date,
                    'left_station': query.left_station,
                    'arrive_station': query.arrive_station,
                    'passengers': query.passengers,
                },
                'ticket': {
                    'left_date': ticket.left_date,
                    'hash_id': ticket.hash_id,
                    'train_number': ticket.train_number,
                    'secret_str': ticket.secret_str,
                    'available_seat': ticket.available_seat,
                    'member_num_take': ticket.member_num_take,
                }
            }))
        else:
            # TODO
            if self._last_notifaction_at and (datetime.datetime.now() - self._last_notifaction_at).seconds < 60:
                Logger.info(f'{ticket.train_number} 通知间隔过短，跳过本次通知')
            else:
                self._last_notifaction_at = datetime.datetime.now()
                await Notification.ticket_available_notifation(ticket)
                Logger.info('余票提醒信息发送成功！')
        await ticket.save()
        await query.save()

    def stop(self):
        if self.is_stoped:
            return
        self._is_stop = True
        Logger.info(f'# 任务 id {self.query.id}，{self.query.left_station} - {self.query.arrive_station} 已退出 #')

    @property
    def is_stoped(self):
        return self._is_stop

    @property
    def is_runable(self):
        return not self._is_stop and self.query.is_queryable
