import re
from typing import List

from py12306.app.app import Logger
from py12306.lib.api import API_QUERY_INIT_PAGE, API_LEFT_TICKETS
from py12306.lib.exceptions import RetryException
from py12306.lib.func import retry, number_of_time_period
from py12306.lib.helper import DataHelper, TrainSeat
from py12306.lib.request import Request


class TicketSeatData(DataHelper):
    name: str
    num: str
    raw: str


class QueryTicketData(DataHelper):
    left_date: str
    left_station: str
    arrive_station: str
    left_periods: List[tuple] = []
    allow_train_numbers: List[str] = []
    execpt_train_numbers: List[str] = []
    allow_seats: List[str] = []
    available_seat: TicketSeatData
    members: list
    member_num: int
    less_member: bool = False

    def _after(self):
        self.member_num = len(self.members)


class TicketData(DataHelper):
    left_date: str = 'key:13'
    ticket_num: str = 'key:11'
    train_number: str = 'key:3'
    train_no: str = 'key:2'
    train_no: str = 'key:2'
    left_station: str = 'key:6'
    arrive_station: str = 'key:7'
    order_text: str = 'key:1'
    secret_str: str = 'key:0'
    left_time: str = 'key:8'
    arrive_time: str = 'key:9'


class Query:
    @classmethod
    def task_train_ticket(cls, task: dict):
        QueryTicket().query_with_info(task)


class QueryTicket:
    """
    车票查询
    """
    api_type: str = None
    time_out: int = 5
    session: Request

    def __init__(self):
        self.session = Request()

    def query_with_info(self, info: dict):
        pass

    @retry()
    def get_query_api_type(self) -> str:
        """
        动态获取查询的接口， 如 leftTicket/query
        :return:
        """
        if QueryTicket.api_type:
            return QueryTicket.api_type
        response = self.session.get(API_QUERY_INIT_PAGE)
        if response.status_code == 200:
            res = re.search(r'var CLeftTicketUrl = \'(.*)\';', response.text)
            try:
                QueryTicket.api_type = res.group(1)
            except IndexError:
                raise RetryException('获取车票查询地址失败')
        return self.get_query_api_type()

    @retry()
    def get_ticket(self, data: dict):
        data = QueryTicketData(data)
        url = API_LEFT_TICKETS.format(left_date=data.left_date, left_station=data.left_station,
                                      arrive_station=data.arrive_station, type=self.get_query_api_type())
        resp = self.session.get(url, timeout=self.time_out, allow_redirects=False)
        result = resp.json().get('data.result')
        if not result:
            Logger.error('车票查询失败, %s' % resp.reason)
        tickets = QueryParser.parse_ticket(result)
        for ticket in tickets:
            self.is_ticket_valid(ticket, data)
            if not data:
                continue
            # 验证完成，准备下单
            Logger.info('[ 查询到座位可用 出发时间 {left_date} 车次 {train_number} 座位类型 {seat_type} 余票数量 {rest_num} ]'.format(
                left_date=data.left_date, train_number=ticket.train_number, seat_type=data.available_seat.name,
                rest_num=data.available_seat.raw))

    def is_ticket_valid(self, ticket: TicketData, query: QueryTicketData) -> bool:
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

        if not self.verify_period(ticket.left_time, query.left_periods):
            return False

        if query.allow_train_numbers and ticket.train_no.upper() not in map(str.upper, query.allow_train_numbers):
            return False

        if query.execpt_train_numbers and ticket.train_no.upper() in map(str.upper, query.execpt_train_numbers):
            return False

        if not self.verify_seat(ticket, query):
            return False
        if not self.verify_member_count(query):
            return False

        return True

    @staticmethod
    def verify_period(period: str, available_periods: List[tuple]):
        if not available_periods:
            return True
        period = number_of_time_period(period)
        for available_period in available_periods:
            if period < number_of_time_period(available_period[0]) or period > number_of_time_period(
                    available_period[1]):
                return False
        return True

    @staticmethod
    def verify_ticket_num(ticket: TicketData):
        return ticket.ticket_num == 'Y' and ticket.order_text == '预订'

    def verify_seat(self, ticket: TicketData, query: QueryTicketData) -> bool:
        """
        检查座位是否可用
        TODO 小黑屋判断   通过 车次 + 座位
        :param ticket:
        :param query:
        :return:
        """
        allow_seats = query.allow_seats
        for seat in allow_seats:
            seat_num = TrainSeat.types[seat]
            raw = ticket.get_origin()[seat_num]
            if self.verify_seat_text(raw):
                query.available_seat = TicketSeatData({
                    'name': seat,
                    'num': seat_num,
                    'raw': raw
                })
                return True
        return False

    @staticmethod
    def verify_seat_text(seat: str) -> bool:
        return seat != '' and seat != '无' and seat != '*'

    @staticmethod
    def verify_member_count(query: QueryTicketData) -> bool:
        seat = query.available_seat
        if not (seat.raw == '有' or query.member_num <= int(seat.raw)):
            rest_num = int(seat.raw)
            if query.less_member:
                query.member_num = rest_num
                Logger.info(
                    '余票数小于乘车人数，当前余票数: %d, 实际人数 %d, 删减人车人数到: %d' % (rest_num, query.member_num, query.member_num))
            else:
                Logger.info('余票数 %d 小于乘车人数 %d，放弃此次提交机会' % (rest_num, query.member_num))
                return False
        return True


class QueryParser:
    @classmethod
    def parse_ticket(cls, items: List[dict]) -> List[TicketData]:
        res = []
        for item in items:
            info = item.split('|')
            info = {i: info[i] for i in range(0, len(info))}  # conver to dict
            res.append(TicketData(info))

        return res
