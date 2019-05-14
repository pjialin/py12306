import re

from py12306.app.app import Logger
from py12306.lib.api import API_QUERY_INIT_PAGE
from py12306.lib.exceptions import RetryException
from py12306.lib.func import retry
from py12306.lib.helper import ShareInstance
from py12306.lib.request import Request


class Query:
    @classmethod
    def task_train_ticket(cls, task: dict):
        QueryTicket().query_with_info(task)


class QueryTicket:
    """
    车票查询
    """
    api_type: str = None

    def __init__(self):
        self.session = Request()

    def query_with_info(self, info: dict):
        pass

    @retry()
    def get_query_api_type(self) -> str:
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
