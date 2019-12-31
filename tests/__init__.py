import asyncio
from functools import wraps
from unittest import TestCase

from tortoise import Tortoise

from app.app import Config, App


def async_test(func):
    """ Async test support """

    @wraps(func)
    def warp(*args, **kwargs):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(func(*args, **kwargs))

    return warp


async def __init_db():
    await Tortoise.init(db_url='sqlite://:memory:', modules={'models': ['app.models']})
    await Tortoise.generate_schemas()


@async_test
async def __init_test():
    await __init_db()
    Config.load()
    await App._App__load_data()


__init_test()


class BaseTest(TestCase):
    @classmethod
    @async_test
    async def tearDownClass(cls) -> None:
        super().tearDownClass()
        await Tortoise.close_connections()
