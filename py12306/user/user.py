from py12306.helpers.app import *
from py12306.helpers.func import *
from py12306.log.user_log import UserLog
from py12306.user.job import UserJob


@singleton
class User:
    heartbeat = 60 * 2
    users = []

    retry_time = 3

    def __init__(self):
        self.interval = config.USER_HEARTBEAT_INTERVAL

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

    @classmethod
    def get_user(cls, key):
        self = cls()
        for user in self.users:
            if user.key == key:
                return user
        return None

    @classmethod
    def check_members(cls, members, key, call_back):
        """
        检测乘客信息
        :param passengers:
        :return:
        """
        self = cls()

        for user in self.users:
            assert isinstance(user, UserJob)
            if user.key == key and user.check_is_ready():
                passengers = user.get_passengers_by_members(members)
                return call_back(passengers)

        UserLog.add_quick_log(UserLog.MESSAGE_WAIT_USER_INIT_COMPLETE.format(self.retry_time)).flush()
        stay_second(self.retry_time)
        return self.check_members(members, key, call_back)
