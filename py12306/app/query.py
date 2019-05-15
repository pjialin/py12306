import re
from typing import List

from py12306.app.app import Logger
from py12306.lib.api import API_QUERY_INIT_PAGE, API_LEFT_TICKETS
from py12306.lib.exceptions import RetryException
from py12306.lib.func import retry
from py12306.lib.helper import DataHelper
from py12306.lib.request import Request


class QueryTicketData(DataHelper):
    left_date: str
    left_station: str
    arrive_station: str


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


class QueryParser:
    @classmethod
    def parse_ticket(cls, items: dict) -> List[TicketData]:
        res = []
        for item in items:
            info = item.split('|')
            info = {i: info[i] for i in range(0, len(info))}  # conver to dict
            res.append(TicketData(info))

        return res
