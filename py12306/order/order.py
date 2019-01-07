from py12306.helpers.app import *
from py12306.helpers.func import *
from py12306.log.user_log import UserLog
from py12306.user.job import UserJob


class Order:
    """
    处理下单
    """
    heartbeat = 60 * 2
    users = []

    def __init__(self):
        pass

    @classmethod
    def run(cls):
        self = cls()
        app_available_check()
        self.start()
        pass

    def start(self):
        self.init_users()
        UserLog.print_init_users(users=self.users)
        # 多线程维护用户
        create_thread_and_run(jobs=self.users, callback_name='run', wait=False)

    def init_users(self):
        accounts = config.USER_ACCOUNTS
        for account in accounts:
            user = UserJob(info=account, user=self)
            self.users.append(user)
