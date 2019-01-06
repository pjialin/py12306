from py12306.helpers.func import *
from py12306.log.user_log import UserLog
from py12306.user.job import UserJob


@singleton
class User:
    heartbeat = 60 * 2
    users = []

    def __init__(self):
        self.interval = config.USER_HEARTBEAT_INTERVAL

    @classmethod
    def run(cls):
        self = cls()
        self.start()
        pass

    def start(self):
        self.init_users()
        UserLog.print_init_users(users=self.users)
        while True:
            # 多线程维护用户
            threads = []
            for user in self.users:
                thread = threading.Thread(target=user.run)
                thread.start()
                threads.append(thread)
                # user.run()
            for thread in threads: thread.join()

    def init_users(self):
        accounts = config.USER_ACCOUNTS
        for account in accounts:
            user = UserJob(info=account, user=self)
            self.users.append(user)
