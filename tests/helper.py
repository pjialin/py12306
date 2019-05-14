from unittest import TestCase

from py12306.app.app import Config
from py12306.lib.redis_lib import Redis


class BaseTest(TestCase):
    redis: Redis = None
    config: Config = None

    def setUp(self) -> None:
        super().setUp()
        Config.TEST_MODE = True
        self.config = Config
        self.redis = Redis.share()
