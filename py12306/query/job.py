import sys
from datetime import timedelta

from py12306.app import app_available_check
from py12306.cluster.cluster import Cluster
from py12306.config import Config
from py12306.helpers.api import LEFT_TICKETS
from py12306.helpers.station import Station
from py12306.helpers.type import OrderSeatType, SeatType
from py12306.log.query_log import QueryLog
from py12306.helpers.func import *
from py12306.log.user_log import UserLog
from py12306.order.order import Order
from py12306.user.user import User
from py12306.helpers.event import Event


class Job:
    """
    查询任务
    """
    id = 0
    is_alive = True
    job_name = None
    left_dates = []
    left_date = None
    stations = []
    left_station = ''
    arrive_station = ''
    left_station_code = ''
    arrive_station_code = ''
    from_time = timedelta(hours=0)
    to_time = timedelta(hours=24)

    account_key = 0
    allow_seats = []
    current_seat = None
    current_seat_name = ''
    current_order_seat = None
    allow_train_numbers = []
    except_train_numbers = []
    members = []
    member_num = 0
    member_num_take = 0  # 最终提交的人数
    passengers = []
    allow_less_member = False
    retry_time = 3

    interval = {}
    interval_additional = 0
    interval_additional_max = 5

    query = None
    cluster = None
    ticket_info = {}
    is_cdn = False
    query_time_out = 3
    INDEX_TICKET_NUM = 11
    INDEX_TRAIN_NUMBER = 3
    INDEX_TRAIN_NO = 2
    INDEX_LEFT_DATE = 13
    INDEX_LEFT_STATION = 6  # 4 5 始发 终点
    INDEX_ARRIVE_STATION = 7
    INDEX_ORDER_TEXT = 1  # 下单文字
    INDEX_SECRET_STR = 0
    INDEX_LEFT_TIME = 8
    INDEX_ARRIVE_TIME = 9

    def __init__(self, info, query):
        self.cluster = Cluster()
        self.query = query
        self.init_data(info)
        self.update_interval()

    def init_data(self, info):
        self.id = md5(info)
        self.left_dates = info.get('left_dates')
        self.stations = info.get('stations')
        self.stations = [self.stations] if isinstance(self.stations, dict) else self.stations
        if not self.job_name:  # name 不能被修改
            self.job_name = info.get('job_name',
                                     '{} -> {}'.format(self.stations[0]['left'], self.stations[0]['arrive']))

        self.account_key = str(info.get('account_key'))
        self.allow_seats = info.get('seats')
        self.allow_train_numbers = info.get('train_numbers')
        self.except_train_numbers = info.get('except_train_numbers')
        self.members = list(map(str, info.get('members')))
        self.member_num = len(self.members)
        self.member_num_take = self.member_num
        self.allow_less_member = bool(info.get('allow_less_member'))
        period = info.get('period')
        if isinstance(period, dict):
            if 'from' in period:
                parts = period['from'].split(':')
                if len(parts) == 2:
                    self.from_time = timedelta(
                        hours=int(parts[0]), seconds=int(parts[1]))
            if 'to' in period:
                parts = period['to'].split(':')
                if len(parts) == 2:
                    self.to_time = timedelta(
                        hours=int(parts[0]), seconds=int(parts[1]))

    def update_interval(self):
        self.interval = self.query.interval

    def run(self):
        self.start()

    def start(self):
        """
        处理单个任务
        根据日期循环查询, 展示处理时间
        :param job:
        :return:
        """
        while True and self.is_alive:
            app_available_check()
            QueryLog.print_job_start(self.job_name)
            for station in self.stations:
                self.refresh_station(station)
                for date in self.left_dates:
                    self.left_date = date
                    response = self.query_by_date(date)
                    self.handle_response(response)
                    QueryLog.add_query_time_log(time=response.elapsed.total_seconds(), is_cdn=self.is_cdn)
                    if not self.is_alive: return
                    self.safe_stay()
                    if is_main_thread():
                        QueryLog.flush(sep='\t\t', publish=False)
            if not Config().QUERY_JOB_THREAD_ENABLED:
                QueryLog.add_quick_log('').flush(publish=False)
                break
            else:
                QueryLog.add_log('\n').flush(sep='\t\t', publish=False)
            if Const.IS_TEST: return

    def query_by_date(self, date):
        """
        通过日期进行查询
        :return:
        """
        from py12306.helpers.cdn import Cdn
        QueryLog.add_log(('\n' if not is_main_thread() else '') + QueryLog.MESSAGE_QUERY_START_BY_DATE.format(date,
                                                                                                              self.left_station,
                                                                                                              self.arrive_station))
        url = LEFT_TICKETS.get('url').format(left_date=date, left_station=self.left_station_code,
                                             arrive_station=self.arrive_station_code, type='leftTicket/queryZ')
        if Config.is_cdn_enabled() and Cdn().is_ready:
            self.is_cdn = True
            return self.query.session.cdn_request(url, timeout=self.query_time_out, allow_redirects=False)
        self.is_cdn = False
        return self.query.session.get(url, timeout=self.query_time_out, allow_redirects=False)

    def handle_response(self, response):
        """
        错误判断
        余票判断
        小黑屋判断
        座位判断
        乘车人判断
        :param result:
        :return:
        """
        results = self.get_results(response)
        if not results:
            return False
        for result in results:
            self.ticket_info = ticket_info = result.split('|')
            if not self.is_trains_number_valid():  # 车次是否有效
                continue
            QueryLog.add_log(QueryLog.MESSAGE_QUERY_LOG_OF_EVERY_TRAIN.format(self.get_info_of_train_number()))
            if not self.is_has_ticket(ticket_info):
                continue
            allow_seats = self.allow_seats if self.allow_seats else list(
                Config.SEAT_TYPES.values())  # 未设置 则所有可用 TODO  合法检测
            self.handle_seats(allow_seats, ticket_info)
            if not self.is_alive: return

    def handle_seats(self, allow_seats, ticket_info):
        for seat in allow_seats:  # 检查座位是否有票
            self.set_seat(seat)
            ticket_of_seat = ticket_info[self.current_seat]
            if not self.is_has_ticket_by_seat(ticket_of_seat):  # 座位是否有效
                continue
            QueryLog.print_ticket_seat_available(left_date=self.get_info_of_left_date(),
                                                 train_number=self.get_info_of_train_number(), seat_type=seat,
                                                 rest_num=ticket_of_seat)
            if not self.is_member_number_valid(ticket_of_seat):  # 乘车人数是否有效
                if self.allow_less_member:
                    self.member_num_take = int(ticket_of_seat)
                    QueryLog.print_ticket_num_less_than_specified(ticket_of_seat, self)
                else:
                    QueryLog.add_quick_log(
                        QueryLog.MESSAGE_GIVE_UP_CHANCE_CAUSE_TICKET_NUM_LESS_THAN_SPECIFIED).flush()
                    continue
            if Const.IS_TEST: return
            # 检查完成 开始提交订单
            QueryLog.print_ticket_available(left_date=self.get_info_of_left_date(),
                                            train_number=self.get_info_of_train_number(),
                                            rest_num=ticket_of_seat)
            if User.is_empty():
                QueryLog.add_quick_log(QueryLog.MESSAGE_USER_IS_EMPTY_WHEN_DO_ORDER.format(self.retry_time))
                return stay_second(self.retry_time)

            order_result = False
            user = self.get_user()
            if not user:
                QueryLog.add_quick_log(QueryLog.MESSAGE_ORDER_USER_IS_EMPTY.format(self.retry_time))
                return stay_second(self.retry_time)

            lock_id = Cluster.KEY_LOCK_DO_ORDER + '_' + user.key
            if Config().is_cluster_enabled():
                if self.cluster.get_lock(lock_id, Cluster.lock_do_order_time,
                                         {'node': self.cluster.node_name}):  # 获得下单锁
                    order_result = self.do_order(user)
                    if not order_result:  # 下单失败，解锁
                        self.cluster.release_lock(lock_id)
                else:
                    QueryLog.add_quick_log(
                        QueryLog.MESSAGE_SKIP_ORDER.format(self.cluster.get_lock_info(lock_id).get('node'),
                                                           user.user_name))
                    stay_second(self.retry_time)  # 防止过多重复
            else:
                order_result = self.do_order(user)

            # 任务已成功 通知集群停止任务
            if order_result:
                Event().job_destroy({'name': self.job_name})

    def do_order(self, user):
        self.check_passengers()
        order = Order(user=user, query=self)
        return order.order()

    def get_results(self, response):
        """
        解析查询返回结果
        :param response:
        :return:
        """
        if response.status_code != 200:
            QueryLog.print_query_error(response.reason, response.status_code)
            if self.interval_additional < self.interval_additional_max:
                self.interval_additional += self.interval.get('min')
        else:
            self.interval_additional = 0
        result = response.json().get('data.result')
        return result if result else False

    def is_has_ticket(self, ticket_info):
        return self.get_info_of_ticket_num() == 'Y' and self.get_info_of_order_text() == '预订'

    def is_has_ticket_by_seat(self, seat):
        return seat != '' and seat != '无' and seat != '*'

    def is_trains_number_valid(self):
        train_left_time = self.get_info_of_train_left_time()
        time_parts = train_left_time.split(':')
        left_time = timedelta(
            hours=int(time_parts[0]), seconds=int(time_parts[1]))
        if left_time < self.from_time or left_time > self.to_time:
            return False

        if self.except_train_numbers:
            return self.get_info_of_train_number().upper() not in map(str.upper, self.except_train_numbers)
        if self.allow_train_numbers:
            return self.get_info_of_train_number().upper() in map(str.upper, self.allow_train_numbers)
        return True

    def is_member_number_valid(self, seat):
        return seat == '有' or self.member_num <= int(seat)

    def destroy(self):
        """
        退出任务
        :return:
        """
        from py12306.query.query import Query
        self.is_alive = False
        QueryLog.add_quick_log(QueryLog.MESSAGE_QUERY_JOB_BEING_DESTROY.format(self.job_name)).flush()
        # sys.exit(1) # 无法退出线程...
        # 手动移出jobs 防止单线程死循环
        index = Query().jobs.index(self)
        Query().jobs.pop(index)

    def safe_stay(self):
        origin_interval = get_interval_num(self.interval)
        interval = origin_interval + self.interval_additional
        QueryLog.add_stay_log(
            '%s + %s' % (origin_interval, self.interval_additional) if self.interval_additional else origin_interval)
        stay_second(interval)

    def set_passengers(self, passengers):
        UserLog.print_user_passenger_init_success(passengers)
        self.passengers = passengers

    def set_seat(self, seat):
        self.current_seat_name = seat
        self.current_seat = SeatType.dicts.get(seat)
        self.current_order_seat = OrderSeatType.dicts.get(seat)

    def get_user(self):
        user = User.get_user(self.account_key)
        # if not user.check_is_ready(): # 这里不需要检测了，后面获取乘客时已经检测过
        #     #
        #     pass
        return user

    def check_passengers(self):
        if not self.passengers:
            QueryLog.add_quick_log(QueryLog.MESSAGE_CHECK_PASSENGERS.format(self.job_name)).flush()
            passengers = User.get_passenger_for_members(self.members, self.account_key)
            if passengers:
                self.set_passengers(passengers)
            else:  # 退出当前查询任务
                self.destroy()
        return True

    def refresh_station(self, station):
        self.left_station = station.get('left')
        self.arrive_station = station.get('arrive')
        self.left_station_code = Station.get_station_key_by_name(self.left_station)
        self.arrive_station_code = Station.get_station_key_by_name(self.arrive_station)

    # 提供一些便利方法
    def get_info_of_left_date(self):
        return self.ticket_info[self.INDEX_LEFT_DATE]

    def get_info_of_ticket_num(self):
        return self.ticket_info[self.INDEX_TICKET_NUM]

    def get_info_of_train_number(self):
        return self.ticket_info[self.INDEX_TRAIN_NUMBER]

    def get_info_of_train_no(self):
        return self.ticket_info[self.INDEX_TRAIN_NO]

    def get_info_of_left_station(self):
        return Station.get_station_name_by_key(self.ticket_info[self.INDEX_LEFT_STATION])

    def get_info_of_arrive_station(self):
        return Station.get_station_name_by_key(self.ticket_info[self.INDEX_ARRIVE_STATION])

    def get_info_of_order_text(self):
        return self.ticket_info[self.INDEX_ORDER_TEXT]

    def get_info_of_secret_str(self):
        return self.ticket_info[self.INDEX_SECRET_STR]

    def get_info_of_train_left_time(self):
        return self.ticket_info[self.INDEX_LEFT_TIME]

    def get_info_of_train_arrive_time(self):
        return self.ticket_info[self.INDEX_ARRIVE_TIME]
