import pickle
from os import path

from py12306.helpers.api import API_USER_CHECK, API_BASE_LOGIN, API_AUTH_UAMTK, API_AUTH_UAMAUTHCLIENT, API_USER_INFO
from py12306.helpers.app import *
from py12306.helpers.auth_code import AuthCode
from py12306.helpers.func import *
from py12306.helpers.request import Request
from py12306.log.user_log import UserLog


class UserJob:
    heartbeat = 60 * 2  # 心跳保持时长
    heartbeat_interval = 5
    key = None
    user_name = ''
    password = ''
    user = None
    info = {}  # 用户信息
    last_heartbeat = None

    def __init__(self, info, user):
        self.session = Request()
        self.heartbeat = user.heartbeat

        self.key = info.get('key')
        self.user_name = info.get('user_name')
        self.password = info.get('password')
        self.user = user

    def run(self):
        # load user
        self.load_user()
        self.start()

    def start(self):
        """
        检测心跳
        :return:
        """
        while True:
            app_available_check()
            self.check_heartbeat()
            sleep(self.heartbeat_interval)

    def check_heartbeat(self):
        # 心跳检测
        if self.last_heartbeat and (time_now() - self.last_heartbeat).seconds < self.heartbeat:
            return True
        if self.is_first_time() or not self.check_user_is_login():
            self.handle_login()

        UserLog.add_quick_log(UserLog.MESSAGE_USER_HEARTBEAT_NORMAL.format(self.get_name(), self.heartbeat)).flush()
        self.last_heartbeat = time_now()

    # def init_cookies
    def is_first_time(self):
        return not path.exists(self.get_cookie_path())

    def handle_login(self):
        UserLog.print_start_login(user=self)
        self.login()

    def login(self):
        """
        获取验证码结果
        :return 权限校验码
        """
        data = {
            'username': self.user_name,
            'password': self.password,
            'appid': 'otn'
        }
        answer = AuthCode.get_auth_code(self.session)
        data['answer'] = answer
        response = self.session.post(API_BASE_LOGIN.get('url'), data)
        result = response.json()
        if result.get('result_code') == 0:  # 登录成功
            """
            login 获得 cookie uamtk
            auth/uamtk      不请求，会返回 uamtk票据内容为空
            /otn/uamauthclient 能拿到用户名
            """
            new_tk = self.auth_uamtk()
            user_name = self.auth_uamauthclient(new_tk)
            self.update_user_info({'user_name': user_name})
            self.login_did_success()
        elif result.get('result_code') == 2:  # 账号之内错误
            # 登录失败，用户名或密码为空
            # 密码输入错误
            UserLog.add_quick_log(UserLog.MESSAGE_LOGIN_FAIL.format(result.get('result_message')))
        else:
            UserLog.add_quick_log(
                UserLog.MESSAGE_LOGIN_FAIL.format(result.get('result_message', result.get('message', '-'))))

        return False

        pass

    def check_user_is_login(self):
        response = self.session.get(API_USER_CHECK.get('url'))
        is_login = response.json().get('data').get('flag', False)
        if is_login:
            self.save_user()
        return is_login

    def auth_uamtk(self):
        response = self.session.post(API_AUTH_UAMTK.get('url'), {'appid': 'otn'})
        result = response.json()
        if result.get('newapptk'):
            return result.get('newapptk')
        # TODO 处理获取失败情况
        return False

    def auth_uamauthclient(self, tk):
        response = self.session.post(API_AUTH_UAMAUTHCLIENT.get('url'), {'tk': tk})
        result = response.json()
        if result.get('username'):
            return result.get('username')
        # TODO 处理获取失败情况
        return False

    def login_did_success(self):
        """
        用户登录成功
        :return:
        """
        self.welcome_user()
        self.save_user()
        self.get_user_info()
        pass

    def welcome_user(self):
        UserLog.print_welcome_user(self)
        pass

    def get_cookie_path(self):
        return config.USER_DATA_DIR + self.user_name + '.cookie'

    def update_user_info(self, info):
        self.info = {**self.info, **info}

    def get_name(self):
        return self.info.get('user_name')

    def save_user(self):
        with open(self.get_cookie_path(), 'wb') as f:
            pickle.dump(self.session.cookies, f)

    def did_loaded_user(self):
        """
        恢复用户成功
        :return:
        """
        UserLog.add_quick_log(UserLog.MESSAGE_LOADED_USER.format(self.user_name))
        if self.check_user_is_login():
            UserLog.add_quick_log(UserLog.MESSAGE_LOADED_USER_SUCCESS.format(self.user_name))
            self.get_user_info()
            UserLog.print_welcome_user(self)
        else:
            UserLog.add_quick_log(UserLog.MESSAGE_LOADED_USER_BUT_EXPIRED)

    def get_user_info(self):
        response = self.session.get(API_USER_INFO.get('url'))
        result = response.json()
        user_data = result.get('data')
        if user_data.get('userDTO') and user_data['userDTO'].get('loginUserDTO'):
            user_data = user_data['userDTO']['loginUserDTO']
            self.update_user_info({**user_data, **{'user_name': user_data['name']}})
            return True
        return None

    def load_user(self):
        cookie_path = self.get_cookie_path()
        if path.exists(cookie_path):
            with open(self.get_cookie_path(), 'rb') as f:
                self.session.cookies.update(pickle.load(f))
                self.did_loaded_user()
                return True
        return None
