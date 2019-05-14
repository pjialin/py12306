from redis import Redis as PyRedis

from py12306.app.app import Config
from py12306.lib.helper import ShareInstance

import json


class Redis(PyRedis, ShareInstance):

    def __init__(self, **kwargs):
        if not kwargs:
            kwargs = Config.REDIS
        super().__init__(**kwargs)

    def push_task(self, key: str, tasks: dict):
        return self.rpush(key, json.dumps(tasks))

    def get_task_sync(self, keys: list) -> tuple:
        tasks = self.brpop(keys)
        return tasks[0][len(Config.REDIS_PREFIX_KEY_TASKS):], json.loads(tasks[1])


if __name__ == '__main__':
    res = Redis.share().keys('*')
    print(res)
    pass
