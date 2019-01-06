from py12306.log.base import BaseLog
from py12306.helpers.func import *


@singleton
class CommonLog(BaseLog):

    def __init__(self):
        super().__init__()
        self.init_data()

    def init_data(self):
        print('Common Log 初始化')

    @classmethod
    def print_auto_code_fail(cls, reason):
        self = cls()
        self.add_quick_log('打码失败: 错误原因 {reason}'.format(reason=reason))
        self.flush()
        return self
