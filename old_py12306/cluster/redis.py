import json
import pickle

import redis

from py12306.config import Config
from py12306.helpers.func import *
from py12306.log.redis_log import RedisLog
from redis import Redis as PyRedis


@singleton
class Redis(PyRedis):
    # session = None

    def __init__(self, *args):
        if Config.is_cluster_enabled():
            args = {
                'host': Config().REDIS_HOST,
                'port': Config().REDIS_PORT,
                'db': 0,
                'password': Config().REDIS_PASSWORD,
                'decode_responses': True
            }
            super().__init__(**args)
            RedisLog.add_quick_log(RedisLog.MESSAGE_REDIS_INIT_SUCCESS)
        else:
            super().__init__(**args)
        return self

    def get(self, name, default=None):
        res = super().get(name)
        # if decode: res = res.decode()
        return res if res else default

    def set(self, name, value, ex=None, px=None, nx=False, xx=False):
        return super().set(name, available_value(value), ex=ex, px=px, nx=nx, xx=xx)

    def set_dict(self, name, value):
        return self.set_pickle(name, value)
        # return self.set(name, json.dumps(value))

    def get_dict(self, name, default={}):
        return self.get_pickle(name, default)
        # res = self.get(name)
        # if res:
        #     return json.loads(res)
        # return default

    def set_pickle(self, name, value):
        return self.set(name, pickle.dumps(value, 0).decode())

    def get_pickle(self, name, default=None):
        res = self.get(name)
        return pickle.loads(res.encode()) if res else default

    # def smembers(self, name, default=[]):
    #     res = super().smembers(name)
    #     return [val.decode() for val in list(res)] if res else default
