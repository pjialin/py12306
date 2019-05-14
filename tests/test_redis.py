from py12306.lib.redis_lib import Redis
from tests.helper import BaseTest


class TestRedis(BaseTest):

    def test_connection(self):
        res = Redis.share().info()
        self.assertIsInstance(res, dict)
