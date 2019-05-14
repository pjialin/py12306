from py12306.app.app import Logger, Config
from py12306.lib.func import new_thread_with_jobs
from py12306.lib.redis_lib import Redis


def get_routes() -> dict:
    from py12306.app.user import User
    return {
        'user': User.task_user,
        'query': User.task_user,
    }


class Task:
    routes: dict = None

    @classmethod
    def listen(cls):
        routes = get_routes()
        keys = [Config.REDIS_PREFIX_KEY_TASKS + key for key, _ in routes.items()]
        while True:
            key, job = Redis.share().get_task_sync(keys)
            Logger.info('获得新任务 %s' % key)
            if Config.TEST_MODE:  # ignore when in test env
                return job
            self = cls()
            self.routes = routes
            self.deal_job(key, job)

    def deal_job(self, key: str, task: dict):
        handler = self.routes.get(key)
        if not handler:
            return
        new_thread_with_jobs(handler, wait=True, kwargs={'task': task})
