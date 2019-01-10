from py12306.app import *
from py12306.cluster.cluster import Cluster
from py12306.helpers.event import Event
from py12306.helpers.func import *
from py12306.log.user_log import UserLog
from py12306.user.job import UserJob


@singleton
class User:
    users = []
    user_accounts = []

    retry_time = 3
    cluster = None

    def __init__(self):
        self.cluster = Cluster()
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
        return user

    def refresh_users(self, old):
        for account in self.user_accounts:
            key = account.get('key')
            old_account = array_dict_find_by_key_value(old, 'key', key)
            if old_account and account != old_account:
                user = self.get_user(key)
                user.init_data(account)
            elif not old_account:  # 新用户 添加到 多线程
                new_user = self.init_user(account)
                create_thread_and_run(jobs=new_user, callback_name='run', wait=Const.IS_TEST)

        for account in old:  # 退出已删除的用户
            if not array_dict_find_by_key_value(self.user_accounts, 'key', account.get('key')):
                Event().user_job_destroy({'key': account.get('key')})

    @classmethod
    def is_empty(cls):
        self = cls()
        return not bool(self.users)

    @classmethod
    def get_user(cls, key) -> UserJob:
        self = cls()
        for user in self.users:
            if user.key == key: return user
        return None

    @classmethod
    def get_passenger_for_members(cls, members, key):
        """
        检测乘客信息
        :param passengers
        :return:
        """
        self = cls()

        for user in self.users:
            assert isinstance(user, UserJob)
            if user.key == key and user.wait_for_ready():
                return user.get_passengers_by_members(members)
