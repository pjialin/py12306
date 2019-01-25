import json
import pickle
import re
from os import path

from py12306.cluster.cluster import Cluster
from py12306.helpers.api import *
from py12306.app import *
from py12306.helpers.auth_code import AuthCode
from py12306.helpers.event import Event
from py12306.helpers.func import *
from py12306.helpers.request import Request
from py12306.helpers.type import UserType
from py12306.log.order_log import OrderLog
from py12306.log.user_log import UserLog
from py12306.log.common_log import CommonLog


class UserJob:
    # heartbeat = 60 * 2  # 心跳保持时长
    is_alive = True
    check_interval = 5
    key = None
    user_name = ''
    password = ''
    user = None
    info = {}  # 用户信息
    last_heartbeat = None
    is_ready = False
    user_loaded = False  # 用户是否已加载成功
    passengers = []
    retry_time = 3
    login_num = 0  # 尝试登录次数

    # Init page
    global_repeat_submit_token = None
    ticket_info_for_passenger_form = None
    order_request_dto = None

    cluster = None
    lock_init_user_time = 3 * 60
    cookie = False

    def __init__(self, info):
        self.cluster = Cluster()
        self.init_data(info)

    def init_data(self, info):
        self.session = Request()
        self.session.add_response_hook(self.response_login_check)
        self.key = str(info.get('key'))
        self.user_name = info.get('user_name')
        self.password = info.get('password')

    def update_user(self):
        from py12306.user.user import User
        self.user = User()
        self.load_user()

    def run(self):
        # load user
        self.update_user()
        self.start()

    def start(self):
        """
        检测心跳
        :return:
        """
        while True and self.is_alive:
            app_available_check()
            if Config().is_slave():
                self.load_user_from_remote()
            else:
                if Config().is_master() and not self.cookie: self.load_user_from_remote()  # 主节点加载一次 Cookie
                self.check_heartbeat()
            if Const.IS_TEST: return
            stay_second(self.check_interval)

    def check_heartbeat(self):
        # 心跳检测
        if self.get_last_heartbeat() and (time_int() - self.get_last_heartbeat()) < Config().USER_HEARTBEAT_INTERVAL:
            return True
        # 只有主节点才能走到这
        if self.is_first_time() or not self.check_user_is_login():
            if not self.handle_login(): return

        self.user_did_load()
        message = UserLog.MESSAGE_USER_HEARTBEAT_NORMAL.format(self.get_name(), Config().USER_HEARTBEAT_INTERVAL)
        UserLog.add_quick_log(message).flush()

    def get_last_heartbeat(self):
        if Config().is_cluster_enabled():
            return int(self.cluster.session.get(Cluster.KEY_USER_LAST_HEARTBEAT, 0))

        return self.last_heartbeat

    def set_last_heartbeat(self, time=None):
        time = time if time != None else time_int()
        if Config().is_cluster_enabled():
            self.cluster.session.set(Cluster.KEY_USER_LAST_HEARTBEAT, time)
        self.last_heartbeat = time

    # def init_cookies
    def is_first_time(self):
        if Config().is_cluster_enabled():
            return not self.cluster.get_user_cookie(self.key)
        return not path.exists(self.get_cookie_path())

    def handle_login(self, expire=False):
        if expire: UserLog.print_user_expired()
        self.is_ready = False
        UserLog.print_start_login(user=self)
        return self.login()

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
            return True
        elif result.get('result_code') == 2:  # 账号之内错误
            # 登录失败，用户名或密码为空
            # 密码输入错误
            UserLog.add_quick_log(UserLog.MESSAGE_LOGIN_FAIL.format(result.get('result_message'))).flush()
        else:
            UserLog.add_quick_log(
                UserLog.MESSAGE_LOGIN_FAIL.format(result.get('result_message', result.get('message',
                                                                                          CommonLog.MESSAGE_RESPONSE_EMPTY_ERROR)))).flush()

        return False

    def check_user_is_login(self):
        response = self.session.get(API_USER_LOGIN_CHECK)
        is_login = response.json().get('data.is_login', False) == 'Y'
        if is_login:
            self.save_user()
            self.set_last_heartbeat()
            return self.get_user_info()  # 检测应该是不会维持状态，这里再请求下个人中心看有没有用，01-10 看来应该是没用  01-22 有时拿到的状态 是已失效的再加上试试

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
        self.login_num += 1
        self.welcome_user()
        self.save_user()
        self.get_user_info()
        self.set_last_heartbeat()
        self.is_ready = True

    def welcome_user(self):
        UserLog.print_welcome_user(self)
        pass

    def get_cookie_path(self):
        return Config().USER_DATA_DIR + self.user_name + '.cookie'

    def update_user_info(self, info):
        self.info = {**self.info, **info}

    def get_name(self):
        return self.info.get('user_name', '')

    def save_user(self):
        if Config().is_master():
            self.cluster.set_user_cookie(self.key, self.session.cookies)
            self.cluster.set_user_info(self.key, self.info)
        with open(self.get_cookie_path(), 'wb') as f:
            pickle.dump(self.session.cookies, f)

    def did_loaded_user(self):
        """
        恢复用户成功
        :return:
        """
        UserLog.add_quick_log(UserLog.MESSAGE_LOADED_USER.format(self.user_name)).flush()
        if self.check_user_is_login() and self.get_user_info():
            UserLog.add_quick_log(UserLog.MESSAGE_LOADED_USER_SUCCESS.format(self.user_name)).flush()
            UserLog.print_welcome_user(self)
            self.user_did_load()
        else:
            UserLog.add_quick_log(UserLog.MESSAGE_LOADED_USER_BUT_EXPIRED).flush()
            self.set_last_heartbeat(0)

    def user_did_load(self):
        """
        用户已经加载成功
        :return:
        """
        self.is_ready = True
        if self.user_loaded: return
        self.user_loaded = True
        Event().user_loaded({'key': self.key})  # 发布通知

    def get_user_info(self):
        response = self.session.get(API_USER_INFO.get('url'))
        result = response.json()
        user_data = result.get('data.userDTO.loginUserDTO')
        # 子节点访问会导致主节点登录失效 TODO 可快考虑实时同步 cookie
        if user_data:
            self.update_user_info({**user_data, **{'user_name': user_data.get('name')}})
            self.save_user()
            return True
        return False

    def load_user(self):
        if Config().is_cluster_enabled(): return
        cookie_path = self.get_cookie_path()

        if path.exists(cookie_path):
            with open(self.get_cookie_path(), 'rb') as f:
                cookie = pickle.load(f)
                self.cookie = True
                self.session.cookies.update(cookie)
                self.did_loaded_user()
                return True
        return None

    def load_user_from_remote(self):
        cookie = self.cluster.get_user_cookie(self.key)
        info = self.cluster.get_user_info(self.key)
        if Config().is_slave() and (not cookie or not info):
            while True:  # 子节点只能取
                UserLog.add_quick_log(UserLog.MESSAGE_USER_COOKIE_NOT_FOUND_FROM_REMOTE.format(self.user_name)).flush()
                stay_second(self.retry_time)
                return self.load_user_from_remote()
        if info: self.info = info
        if cookie:
            self.session.cookies.update(cookie)
            if not self.cookie:  # 第一次加载
                self.cookie = True
                if not Config().is_slave():
                    self.did_loaded_user()
                else:
                    self.is_ready = True  # 设置子节点用户 已准备好
                    UserLog.print_welcome_user(self)
            return True
        return False

    def check_is_ready(self):
        return self.is_ready

    def wait_for_ready(self):
        if self.is_ready: return self
        UserLog.add_quick_log(UserLog.MESSAGE_WAIT_USER_INIT_COMPLETE.format(self.retry_time)).flush()
        stay_second(self.retry_time)
        return self.wait_for_ready()

    def destroy(self):
        """
        退出用户
        :return:
        """
        UserLog.add_quick_log(UserLog.MESSAGE_USER_BEING_DESTROY.format(self.user_name)).flush()
        self.is_alive = False

    def response_login_check(self, response, **kwargs):
        if Config().is_master() and response.json().get('data.noLogin') == 'true':  # relogin
            self.handle_login(expire=True)

    def get_user_passengers(self):
        if self.passengers: return self.passengers
        response = self.session.post(API_USER_PASSENGERS)
        result = response.json()
        if result.get('data.normal_passengers'):
            self.passengers = result.get('data.normal_passengers')
            # 将乘客写入到文件
            with open(Config().USER_PASSENGERS_FILE % self.user_name, 'w', encoding='utf-8') as f:
                f.write(json.dumps(self.passengers, indent=4, ensure_ascii=False))
            return self.passengers
        else:
            UserLog.add_quick_log(
                UserLog.MESSAGE_GET_USER_PASSENGERS_FAIL.format(
                    result.get('messages', CommonLog.MESSAGE_RESPONSE_EMPTY_ERROR), self.retry_time)).flush()
            if Config().is_slave():
                self.load_user_from_remote() # 加载最新 cookie
            stay_second(self.retry_time)
            return self.get_user_passengers()

    def get_passengers_by_members(self, members):
        """
        获取格式化后的乘客信息
        :param members:
        :return:
        [{
            name: '项羽',
            type: 1,
            id_card: 0000000000000000000,
            type_text: '成人'
        }]
        """
        self.get_user_passengers()
        results = []
        for member in members:
            is_member_code = is_number(member)
            if not is_member_code:
                child_check = array_dict_find_by_key_value(results, 'name', member)
            if not is_member_code and child_check:
                new_member = child_check.copy()
                new_member['type'] = UserType.CHILD
                new_member['type_text'] = dict_find_key_by_value(UserType.dicts, int(new_member['type']))
            else:
                if is_member_code:
                    passenger = array_dict_find_by_key_value(self.passengers, 'code', member)
                else:
                    passenger = array_dict_find_by_key_value(self.passengers, 'passenger_name', member)
                if not passenger:
                    UserLog.add_quick_log(
                        UserLog.MESSAGE_USER_PASSENGERS_IS_INVALID.format(self.user_name, member)).flush()
                    return False
                new_member = {
                    'name': passenger.get('passenger_name'),
                    'id_card': passenger.get('passenger_id_no'),
                    'id_card_type': passenger.get('passenger_id_type_code'),
                    'mobile': passenger.get('mobile_no'),
                    'type': passenger.get('passenger_type'),
                    'type_text': dict_find_key_by_value(UserType.dicts, int(passenger.get('passenger_type')))
                }
            results.append(new_member)

        return results

    def request_init_dc_page(self):
        """
        请求下单页面 拿到 token
        :return:
        """
        data = {'_json_att': ''}
        response = self.session.post(API_INITDC_URL, data)
        html = response.text
        token = re.search(r'var globalRepeatSubmitToken = \'(.+?)\'', html)
        form = re.search(r'var ticketInfoForPassengerForm *= *(\{.+\})', html)
        order = re.search(r'var orderRequestDTO *= *(\{.+\})', html)
        # 系统忙，请稍后重试
        if html.find('系统忙，请稍后重试') != -1:
            OrderLog.add_quick_log(OrderLog.MESSAGE_REQUEST_INIT_DC_PAGE_FAIL).flush()  # 重试无用，直接跳过
            return False
        try:
            self.global_repeat_submit_token = token.groups()[0]
            self.ticket_info_for_passenger_form = json.loads(form.groups()[0].replace("'", '"'))
            self.order_request_dto = json.loads(order.groups()[0].replace("'", '"'))
        except:
            pass  # TODO Error

        return True
