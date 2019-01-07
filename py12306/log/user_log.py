from py12306.log.base import BaseLog
from py12306.helpers.func import *


@singleton
class UserLog(BaseLog):
    MESSAGE_DOWNLAOD_AUTH_CODE_FAIL = '验证码下载失败 错误原因: {} {} 秒后重试'
    MESSAGE_DOWNLAODING_THE_CODE = '正在下载验证码...'
    MESSAGE_CODE_AUTH_FAIL = '验证码验证失败 错误原因: {} {} 秒后重试'
    MESSAGE_CODE_AUTH_SUCCESS = '验证码验证成功 开始登录...'
    MESSAGE_LOGIN_FAIL = '登录失败 错误原因: {}'
    MESSAGE_LOADED_USER = '正在尝试恢复用户: {}'
    MESSAGE_LOADED_USER_SUCCESS = '用户恢复成功: {}'
    MESSAGE_LOADED_USER_BUT_EXPIRED = '用户状态已过期，正在重新登录'
    MESSAGE_USER_HEARTBEAT_NORMAL = '用户 {} 心跳正常，下次检测 {} 秒后'

    MESSAGE_GET_USER_PASSENGERS_FAIL = '获取用户乘客列表失败，错误原因: {} {} 秒后重试'
    MESSAGE_USER_PASSENGERS_IS_INVALID = '乘客信息校验失败，在账号 {} 中未找到该乘客: {}'

    MESSAGE_WAIT_USER_INIT_COMPLETE = '未找到可用账号或用户正在初始化，{} 秒重试'

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
        self.flush()
        return self

    @classmethod
    def print_welcome_user(cls, user):
        self = cls()
        self.add_log('# 欢迎回来，{} #'.format(user.get_name()))
        self.flush()
        return self

    @classmethod
    def print_start_login(cls, user):
        self = cls()
        self.add_log('正在登录用户 {}'.format(user.user_name))
        self.flush()
        return self

    @classmethod
    def print_user_passenger_init_success(cls, passengers):
        self = cls()
        result = [passenger.get('name') + '(' + passenger.get('type_text') + ')' for passenger in passengers]
        self.add_quick_log('# 乘客验证成功 {} #'.format(', '.join(result)))
        self.flush()
        return self
