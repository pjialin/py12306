from tests.helper import BaseTest
from py12306.app.task import Task


class TestTask(BaseTest):
    def test_push_task(self):
        tasks = {
            'query': {
                'name': 'admin',
            },
            'user': {
                'name': 'admin',
                'password': 'password'
            }
        }
        for key, task in tasks.items():
            self.redis.push_task(self.config.REDIS_PREFIX_KEY_TASKS + key, task)

        res = Task.listen()
        self.assertIsInstance(res, dict)
