from tests.helper import BaseTest
from py12306.app.query import QueryTicket


class TestQueryTicket(BaseTest):
    task = {
        'name': 'admin',
    }

    def test_get_query_api_type(self):
        res = QueryTicket().get_query_api_type()
        self.assertEqual('leftTicket/query', res)
