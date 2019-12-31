import asyncio
import datetime

from app.app import Event, Cache
from lib.exceptions import RetryException, MaxRetryException
from lib.hammer import EventItem
from lib.helper import StationHelper, json_friendly_loads, retry
from lib.request import Session
from tests import BaseTest, async_test


class HelperTests(BaseTest):

    def setUp(self) -> None:
        super().setUp()

    @async_test
    async def test_async_retry(self):
        @retry(4)
        async def test():
            raise RetryException()

        with self.assertRaises(MaxRetryException):
            await test()

    def test_retry(self):
        @retry()
        def test():
            raise RetryException()

        with self.assertRaises(MaxRetryException):
            test()

    def test_json_friendly_loads(self):
        ret = json_friendly_loads('["2019-01-25 08:01:56", "2019-12-26"]')
        self.assertEqual(ret[0], datetime.datetime(2019, 1, 25, 8, 1, 56))
        self.assertEqual(ret[1], datetime.datetime(2019, 12, 26).date())


class RequestTests(BaseTest):
    def setUp(self) -> None:
        super().setUp()
        self.session = Session.share()

    @async_test
    async def test_requset(self):
        ret = await self.session.request('GET', 'http://httpbin.org/get')
        result = ret.json()
        self.assertEqual(result.get('headers.Host'), 'httpbin.org')

    def test_cookie_dumps_and_loads(self):
        self.session.session.cookie_jar.update_cookies({
            'test': 'val'
        })
        ret = self.session.cookie_dumps()
        new_session = Session()
        new_session.cookie_loads(ret)
        for cookie in self.session.session.cookie_jar:
            self.assertIn(cookie, new_session.session.cookie_jar)


class StationHelperTests(BaseTest):

    def test_stations(self):
        ret = StationHelper.stations()
        self.assertGreater(len(ret), 1)

    def test_cn_by_id(self):
        ret = StationHelper.cn_by_id('CUW')
        self.assertEqual(ret, '重庆北')


class EventHammerTests(BaseTest):

    @async_test
    async def test_main(self):
        item = EventItem('test', 'data')

        async def subscribe():
            ret = await Event.subscribe()
            self.assertEqual(ret.dumps(), item.dumps())

        asyncio.ensure_future(subscribe())
        second = 5
        while second:
            await Event.publish(item)
            await asyncio.sleep(1)
            second -= 1


class CacheHammerTests(BaseTest):

    @async_test
    async def test_set_get(self):
        await Cache.set('test', 'val')
        ret = await Cache.get('test')
        self.assertEqual(ret, 'val')
        ret = await Cache.get('__test', 'default')
        self.assertEqual(ret, 'default')

    @async_test
    async def test_hash(self):
        await Cache.hset('user', 'name', 'li')
        ret = await Cache.hget('user', 'name')
        self.assertEqual(ret, 'li')
        await Cache.hdel('user', 'name')
        ret = await Cache.hget('user', 'name')
        self.assertEqual(ret, None)
