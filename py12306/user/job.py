from os import path

from requests_html import HTMLSession

from py12306.helpers.api import API_USER_CHECK, API_BASE_LOGIN
from py12306.helpers.func import *


class UserJob:
    heartbeat = 60 * 2
    key = None
    user_name: ''
    password: ''
    user: None

    def __init__(self, info, user):
        self.session = HTMLSession()
        # cookie TODO
        self.heartbeat = user.heartbeat

        self.key = info.get('key')
        self.user_name = info.get('user_name')
        self.password = info.get('password')
        self.user = user

    def run(self):
        self.start()

    def start(self):
        self.check_heartbeat()

    def check_heartbeat(self):
        if self.is_first_time() or not self.check_user_is_login():
            self.handle_login()
        pass

    # def init_cookies
    def is_first_time(self):
        return not self.get_user_cookie()

    def handle_login(self):
        self.base_login()

    def base_login(self):
        """
        获取验证码结果
        :return:
        """
        data = {
            'username': self.user_name,
            'password': self.password,
            'appid': 'otn'
        }
        response = self.session.post(API_BASE_LOGIN.get('url'), data)
        pass

    def check_user_is_login(self):
        response = self.session.get(API_USER_CHECK.get('url'))
        is_login = response.json().get('status')

    def get_user_cookie(self):
        path = self.get_cookie_path()
        if path.exists(path):
            return open(path, encoding='utf-8').read()
        return None

    def get_cookie_path(self):
        return config.USER_DATA_DIR + '/' + self.user_name + '.cookie'
