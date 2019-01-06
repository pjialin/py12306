from py12306.log.base import BaseLog
from py12306.helpers.func import *


@singleton
class UserLog(BaseLog):

    def __init__(self):
        super().__init__()
        self.init_data()

    def init_data(self):
        print('User Log 初始化')

    @classmethod
    def print_init_users(cls, users):
        """
        输出初始化信息
        :return:
        """
        self = cls()
        self.add_log('================== 发现 {} 个用户 =================='.format(len(users)))
        self.add_log('')
        self.flush()
        return self
