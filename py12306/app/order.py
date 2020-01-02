import asyncio
import datetime
import json
import random
import re

from app.app import Event, Cache, Notification
from app.app import Logger, Config
from app.models import QueryJob, User, Order, Ticket
from app.notification import NotifactionMessage
from app.user import TrainUser, TrainUserManager
from lib.exceptions import RetryException
from lib.helper import StationHelper, UserTypeHelper, TrainSeat, TaskManager, retry


class OrderTicketManager(TaskManager):

    async def run(self):
        self.fuatures.append(asyncio.ensure_future(self.subscribe_loop()))
        await self.wait()

    @property
    async def task_total(self) -> int:
        return 0

    async def subscribe_loop(self):
        while True:
            event = await Event.subscribe()
            if event.name == Event.EVENT_ORDER_TICKET:
                await self.handle_order_task(event.data)

    async def handle_order_task(self, data: dict):
        """ 处理订单任务 """
        try:
            user_id = data['user_id']
            train_user: TrainUser = TrainUserManager.share().get_task(user_id)
            if not train_user or not train_user.is_ready:
                Logger.warning(f'用户 ID {user_id} 不可用，已跳过该下单任务')
                return
            # make order model
            query_job = QueryJob(**data['query_job'])
            ticket = Ticket(**data['ticket'])

            Logger.info(f'# 任务 {query_job.current_route_text} 开始下单 #')
            future = asyncio.ensure_future(OrderTicket(query_job, ticket, train_user).order())
            self.fuatures.append(future)
        except Exception as e:
            Logger.error(f'订单任务解析失败，{e}')


class OrderTicket:
    """ 处理下单 """

    def __init__(self, query_job: QueryJob, ticket: Ticket, train_user: TrainUser):
        self.session = train_user.session
        self.query: QueryJob = query_job
        self.user: User = train_user.user
        self.ticket: Ticket = ticket
        self.train_user = train_user
        self._order = Order()
        # Init page
        self.global_repeat_submit_token = None
        self.ticket_info_for_passenger_form = None
        self.order_request_dto = None
        # Config
        self.max_queue_wait = 60 * 5
        self._passenger_ticket_str = ''
        self._old_passenger_str = ''
        self._order_id = ''

    async def order(self):
        """ 开始下单 """
        try:
            while True:
                if self.train_user.is_ordering:
                    await asyncio.sleep(1)
                    continue
                if await Cache.in_dark_room(self.ticket.baby):
                    self._order.status = self._order.Status.DarkRoom
                    return
                break
            self.train_user.is_ordering = True
            return await self.normal_order()
        except Exception as err:
            self._order.status = self._order.Status.Error
            self._order.last_error = str(err)
        finally:
            self.train_user.is_ordering = False
            # 更新为正确的关联信息
            self.user = self.user
            self._order.query_job = await QueryJob.filter(hash_id=self.query.hash_id).first()
            if self._order_id and self._order.query_job:  # 更新订单状态
                self._order.query_job.status = self._order.query_job.Status.Finished
                await self._order.query_job.save()
                self._order.status = self._order.Status.Success
            self._order.ticket = await Ticket.filter(hash_id=self.ticket.hash_id).first()
            await self._order.save()

    async def normal_order(self):
        """ 下单
        ) 提交下单请求
        """
        try:
            order_request_res = await self.submit_order_request()
            if not order_request_res:
                return
            if not await self.request_init_dc_page():
                return
            if not await self.check_order_info():
                return
            if not await self.get_queue_count():
                return
            if not await self.confirm_order_queue():
                return
            order_status = await self.wait_order_queue()
            if order_status and self._order_id:  # 发送通知
                await self.order_did_success(self._order_id)
                return True
            return False
        finally:
            pass

    async def order_did_success(self, order_id: str):
        """ 下单成功 """
        # 加入小黑屋，防止重复下单
        await self._add_to_dark_room()
        title = f'# 车票购买成功，订单号 {order_id} #'
        content = f"请及时登录12306账号 [{self.user.user_id}]，打开 '未完成订单'，在30分钟内完成支付!\n"
        content += f"车次信息： {self.ticket.train_number} {self.query.left_station} -> {self.query.arrive_station}，乘车日期 {self.ticket.left_date}，席位：{self.ticket.available_seat.get('name')}"
        Logger.info(title)
        await Notification.send_message(NotifactionMessage(title, content, extra={
            'name': self.user.real_name,
            'left_station': self.ticket.left_station,
            'arrive_station': self.ticket.arrive_station,
            'set_type': self.ticket.available_seat.get('name'),
            'orderno': order_id
        }))
        await self.show_no_complete_orders()
        return True

    @retry
    async def submit_order_request(self):
        """ 提交下单请求 """
        data = {
            'secretStr': self.ticket.secret_str_unquote,  # 解密
            'train_date': self.ticket.left_date_order,  # 出发时间
            'back_train_date': self.ticket.left_date_order,  # 返程时间
            'tour_flag': 'dc',  # 旅途类型
            'purpose_codes': 'ADULT',  # 成人 | 学生
            'query_from_station_name': StationHelper.cn_by_id(self.query.left_station),
            'query_to_station_name': StationHelper.cn_by_id(self.query.arrive_station),
        }
        response = await self.session.otn_left_ticket_submit_order_request(data)
        result = response.json()
        if result.get('data') == 'N':
            Logger.info('提交订单成功')
            return True
        else:
            if str(result.get('messages', '')).find('未处理') >= 0:  # 未处理订单
                Logger.error(f"提交订单失败，{result.get('messages')}")
                await self.show_no_complete_orders()
                return False
            Logger.error(f"提交订单失败，{result.get('messages', '未知错误')}")
        return False

    @retry
    async def request_init_dc_page(self):
        """
        请求下单页面 拿到 token
        :return:
        """
        response = await self.train_user.session.otn_confirm_passenger_init_dc()
        html = response.text()
        token = re.search(r'var globalRepeatSubmitToken = \'(.+?)\'', html)
        form = re.search(r'var ticketInfoForPassengerForm *= *({.+\})', html)
        order = re.search(r'var orderRequestDTO *= *({.+\})', html)
        # 系统忙，请稍后重试
        if html.find('系统忙，请稍后重试') != -1:
            raise RetryException('请求初始化订单页面失败')
        try:
            self.global_repeat_submit_token = token.groups()[0]
            self.ticket_info_for_passenger_form = json.loads(form.groups()[0].replace("'", '"'))
            self.order_request_dto = json.loads(order.groups()[0].replace("'", '"'))
        except Exception:
            raise RetryException('请求初始化订单页面失败')

        return True

    @retry
    async def check_order_info(self):
        """ 检查下单信息 """
        self.make_passenger_ticket_str()
        data = {  #
            'cancel_flag': 2,
            'bed_level_order_num': '000000000000000000000000000000',
            'passengerTicketStr': self._passenger_ticket_str,
            'oldPassengerStr': self._old_passenger_str,
            'tour_flag': 'dc',
            'randCode': '',
            'whatsSelect': '1',
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': self.global_repeat_submit_token
        }
        response = await self.session.otn_confirm_passenger_check_order_info(data)
        result = response.json()
        if result.get('data.submitStatus'):  # 成功
            # ifShowPassCode 需要验证码
            Logger.info('检查订单成功')
            if result.get('data.ifShowPassCode') != 'N':
                self.is_need_auth_code = True  # TODO
            # if ( ticketInfoForPassengerForm.isAsync == ticket_submit_order.request_flag.isAsync & & ticketInfoForPassengerForm.queryLeftTicketRequestDTO.ypInfoDetail != "") { 不需要排队检测 js TODO
            return True
        else:
            if result.get('data.checkSeatNum'):
                error = '无法提交的订单! ' + result.get('data.errMsg')
                await self._add_to_dark_room()
            elif not result.get('data.isNoActive'):
                error = result.get('data.errMsg', result.get('messages.0'))
            else:
                error = '出票失败! ' + result.get('data.errMsg')
            Logger.error(f'检查订单失败，{error or response.reason}')
        return False

    @retry
    async def get_queue_count(self):
        """ 获取队列人数 """
        data = {  #
            'train_date': '{} 00:00:00 GMT+0800 (China Standard Time)'.format(
                self.ticket.left_date.strftime("%a %h %d %Y")),
            'train_no': self.ticket_info_for_passenger_form['queryLeftTicketRequestDTO']['train_no'],
            'stationTrainCode': self.ticket_info_for_passenger_form['queryLeftTicketRequestDTO']['station_train_code'],
            'seatType': self.ticket.available_seat.get('order_id'),
            'fromStationTelecode': self.ticket_info_for_passenger_form['queryLeftTicketRequestDTO']['from_station'],
            'toStationTelecode': self.ticket_info_for_passenger_form['queryLeftTicketRequestDTO']['to_station'],
            'leftTicket': self.ticket_info_for_passenger_form['leftTicketStr'],
            'purpose_codes': self.ticket_info_for_passenger_form['purpose_codes'],
            'train_location': self.ticket_info_for_passenger_form['train_location'],
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': self.global_repeat_submit_token,
        }
        response = await self.session.otn_confirm_passenger_get_queue_count(data)
        result = response.json()
        if result.get('status', False):  # 成功
            # "data": { "count": "66", "ticket": "0,73", "op_2": "false", "countT": "0", "op_1": "true" }
            # if result.get('isRelogin') == 'Y': # 重新登录 TODO
            ticket = result.get('data.ticket').split(',')  # 余票列表
            # 这里可以判断 是真实是 硬座还是无座，避免自动分配到无座
            ticket_number = ticket[0]  # 余票
            if ticket_number is not '充足' and int(ticket_number) <= 0:
                if self.ticket.available_seat.get('id') == TrainSeat.NO_SEAT:  # 允许无座
                    ticket_number = ticket[1]
                if not int(ticket_number):  # 跳过无座
                    Logger.error('接口返回实际为无票，跳过本次排队')
                    await self._add_to_dark_room()
                    return False

            if result.get('data.op_2') == 'true':
                Logger.error('排队失败，目前排队人数已经超过余票张数')
                return False

            current_position = int(result.get('data.countT', 0))
            Logger.info(f'获取排队信息成功，目前排队人数 {current_position}, 余票还剩余 {ticket_number} 张')
            return True
        else:
            # 加入小黑屋 TODO
            Logger.error(f"排队失败，错误原因: {result.get('messages', result.get('validateMessages', response.reason))}")
        return False

    @retry
    async def confirm_order_queue(self):
        """ 确认排队 """
        data = {  #
            'passengerTicketStr': self._passenger_ticket_str,
            'oldPassengerStr': self._old_passenger_str,
            'randCode': '',
            'purpose_codes': self.ticket_info_for_passenger_form['purpose_codes'],
            'key_check_isChange': self.ticket_info_for_passenger_form['key_check_isChange'],
            'leftTicketStr': self.ticket_info_for_passenger_form['leftTicketStr'],
            'train_location': self.ticket_info_for_passenger_form['train_location'],
            'choose_seats': '',
            'seatDetailType': '000',
            'whatsSelect': '1',
            'roomType': '00',
            'dwAll': 'N',
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': self.global_repeat_submit_token,
        }

        if self.is_need_auth_code:
            # TODO
            pass

        response = await self.session.otn_confirm_passenger_confirm_single_for_queue(data)
        result = response.json()

        if 'data' in result:
            # "data": { "submitStatus": true }
            if result.get('data.submitStatus'):  # 成功
                Logger.info('# 确认排队成功！#')
                return True
            else:
                Logger.error(f"出票失败，{result.get('data.errMsg', response.reason)}")
                await self._add_to_dark_room()
        else:
            Logger.error(f"提交订单失败，{result.get('messages', response.reason)}")
        return False

    @retry
    async def wait_order_queue(self):
        """ 等待订单排队结果 """
        wait_count = 0
        start_at = datetime.datetime.now()
        while (datetime.datetime.now() - start_at).seconds < self.max_queue_wait:
            # TODO 取消超时订单，待优化
            wait_count += 1
            querys = {  #
                'random': str(random.random())[2:],
                'tourFlag': 'dc',
                '_json_att': '',
                'REPEAT_SUBMIT_TOKEN': self.global_repeat_submit_token,
            }
            response = await self.session.otn_confirm_passenger_query_order_wait_time(querys)
            result = response.json()
            if result.get('status') and 'data' in result:
                """ "data": { "queryOrderWaitTimeStatus": true, "count": 0, "waitTime": -1,
                    "requestId": 6487958947291482523, "waitCount": 0, "tourFlag": "dc", "orderId": "E222646122"}
                """
                result_data = result['data']
                order_id = result_data.get('orderId')
                if order_id:  # 成功
                    self._order_id = order_id
                    return True
                elif 'waitTime' in result_data:
                    # 计算等待时间
                    wait_time = int(result_data.get('waitTime'))
                    if wait_time == -1:  # 成功
                        # /otn/confirmPassenger/resultOrderForDcQueue 请求订单状态 目前不需要 # 不应该走到这
                        return True
                    elif wait_time == -100:  # 重新获取订单号
                        pass
                    elif wait_time >= 0:  # 等待
                        Logger.info(f"排队等待中，排队人数 {result_data.get('waitCount', 0)}，预计还需要 {wait_time} 秒")
                    else:
                        if wait_time == -2 or wait_time == -3:  # -2 失败 -3 订单已撤销
                            Logger.error(f"排队失败，错误原因, {result_data.get('msg')}")
                            return False
                        else:  # 未知原因
                            Logger.error(f"排队失败，错误原因, {result_data.get('msg', wait_time)}")
                            return False

                elif result_data.get('msg'):  # 失败 对不起，由于您取消次数过多，今日将不能继续受理您的订票请求。1月8日您可继续使用订票功能。
                    # TODO 需要增加判断 直接结束
                    Logger.error(f"排队失败，错误原因, {result_data.get('msg')}")
                    return False
            elif result.get('messages') or result.get('validateMessages'):
                Logger.error(f"排队失败，错误原因, {result.get('messages', result.get('validateMessages'))}")
                return False
            else:
                pass
            Logger.info(f'第 {wait_count} 次排队，请耐心等待')
            await asyncio.sleep(1)

        return False

    async def _add_to_dark_room(self):
        Logger.warning(f'# 已将 {self.ticket.dark_room_text} 关入小黑屋 #')
        await Cache.add_dark_room(self.ticket.baby)

    @retry
    async def show_no_complete_orders(self):
        """ 展示未完成订单 """
        response = await self.session.otn_query_my_order_no_complete()
        result = response.json()
        if result.get('status') is True:
            for order in result.get('data.orderDBList', []):
                text = f"\n# 待支付订单号 {order.get('sequence_no')} {order.get('order_date')} #\n"
                text += f"车次 {''.join(order.get('from_station_name_page', []))} - {''.join(order.get('to_station_name_page', []))} {order.get('train_code_page', '')} {order.get('start_train_date_page', '')} 开\n"
                for ticket in order.get('tickets'):
                    text += f"\t- {ticket.get('passengerDTO.passenger_name', '')} {ticket.get('passengerDTO.passenger_id_type_name', '')} {ticket.get('seat_type_name', '')} {ticket.get('coach_no', '')}车{ticket.get('seat_name', '')} {ticket.get('ticket_type_name', '')} {ticket.get('str_ticket_price_page', '')}元 {ticket.get('ticket_status_name', '')}\n"
                Logger.info(text)

    def make_passenger_ticket_str(self):
        """ 生成提交车次的内容 格式：
        1(seatType),0,1(车票类型:ticket_type_codes),张三(passenger_name),1(证件类型:passenger_id_type_code),xxxxxx(passenger_id_no),xxxx(mobile_no),N
        passengerTicketStr:
        张三(passenger_name),1(证件类型:passenger_id_type_code),xxxxxx(passenger_id_no),1_oldPassengerStr
        """
        passenger_tickets = []
        old_passengers = []
        available_passengers = self.query.passengers
        if len(available_passengers) > self.ticket.member_num_take:  # 删除人数
            available_passengers = available_passengers[0:self.ticket.member_num_take]
            del_ret = [passenger.get('name') + '(' + passenger.get('type_text') + ')' for passenger in
                       available_passengers]
            Logger.info(f"# 删减后的乘客列表 {', '.join(del_ret)} #")

        for passenger in available_passengers:
            tmp_str = f"{self.ticket.available_seat.get('order_id')},0,{passenger['type']},{passenger['name']}," \
                      f"{passenger['id_card_type']},{passenger['id_card']},{passenger['mobile']},N,{passenger['enc_str']}_"
            passenger_tickets.append(tmp_str)

            if int(passenger['type']) is not UserTypeHelper.CHILD:
                tmp_old_str = f"{passenger['name']},{passenger['id_card_type']},{passenger['id_card']},{passenger['type']}_"
                old_passengers.append(tmp_old_str)

        self._passenger_ticket_str = ''.join(passenger_tickets).rstrip('_')
        self._old_passenger_str = ''.join(old_passengers).rstrip('_') + '__ _ _'
