from py12306.app import *
from py12306.cluster.cluster import Cluster
from py12306.helpers.func import *
from py12306.log.user_log import UserLog
from py12306.user.job import UserJob


@singleton
class User:
    heartbeat = 60 * 2
    users = []
    user_accounts = []

    retry_time = 3
    cluster = None

    def __init__(self):
        self.cluster = Cluster()
        self.heartbeat = Config().USER_HEARTBEAT_INTERVAL
        self.update_interval()
        self.update_user_accounts()

    def update_user_accounts(self, auto=False, old=None):
        self.user_accounts = Config().USER_ACCOUNTS
        if auto:
            UserLog.add_quick_log(UserLog.MESSAGE_USERS_DID_CHANGED).flush()
            self.refresh_users(old)

    def update_interval(self, auto=False):
        self.interval = Config().USER_HEARTBEAT_INTERVAL
        if auto: jobs_do(self.users, 'update_user')

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
        create_thread_and_run(jobs=self.users, callback_name='run', wait=Const.IS_TEST)

    def init_users(self):
        for account in self.user_accounts:
            self.init_user(account)

    def init_user(self, info):
        user = UserJob(info=info)
        self.users.append(user)

    def refresh_users(self, old):
        for account in self.user_accounts:
            key = account.get('key')
            old_account = array_dict_find_by_key_value(old, 'key', key)
            if old_account and account != old_account:
                user = self.get_user(key)
                user.init_data(account)
            elif not old_account:
                self.init_user(account)
        for account in old:  # 退出已删除的用户
            if not array_dict_find_by_key_value(self.user_accounts, 'key', account.get('key')):
                user = self.get_user(account.get('key'))
                user.destroy()

    @classmethod
    def get_user(cls, key) -> UserJob:
        self = cls()
        for user in self.users:
            if user.key == key: return user
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
