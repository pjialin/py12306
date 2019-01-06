from py12306.log.base import BaseLog
from py12306.helpers.func import *


@singleton
class CommonLog(BaseLog):
    MESSAGE_12306_IS_CLOSED = '当前时间: {}     |       12306 休息时间，程序将在明天早上 6 点自动运行'

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
