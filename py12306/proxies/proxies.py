from py12306.config import Config
from py12306.helpers.func import *
import requests
from py12306.helpers.api import *
from py12306.log.proxy_log import ProxyLog
import random
from os import path
import pickle


@singleton
class Proxy:

    def __init__(self):
        """
        初始化代理类，设置代理类型

        :param proxy_type:  1 -> 使用API获取
                            2 -> 使用proxy_list文件获取
        """
        self.proxy_list = []
        self.proxy_num = 0
        self.wrong_time = 0
        self.last_proxy = None
        self.first = True
        self.data_path = Config().RUNTIME_DIR + 'last_proxy'
        if Config().PROXY_ENABLE:
            if Config().PROXY_TYPE == 2:
                self.read_proxies()
            self.load_proxy()
            self.first = False

    def load_proxy(self):
        if self.first and self.load_proxy_from_file():
            return
        if not self.check_proxies_available():
            Config().PROXY_ENABLE = 0
            ProxyLog.proxy_unavailable()
            self.last_proxy = None
            return None
        if Config().PROXY_ENABLE and Config().PROXY_TYPE == 1:
            self.last_proxy = requests.get(API_PROXY_GET.format(Config().PROXY_API_IP, Config().PROXY_API_PORT)).text
        elif Config().PROXY_ENABLE and Config().PROXY_TYPE == 2:
            self.last_proxy = self.get_proxy_from_file()
        ProxyLog.use_proxy(self.last_proxy)
        self.save_proxy_to_file()
        return self.last_proxy

    def load_proxy_from_file(self):
        if path.exists(self.data_path):
            with open(self.data_path, 'rb') as f:
                self.last_proxy = pickle.load(f)
            ProxyLog.add_quick_log('加载上次使用的代理IP: {}'.format(self.last_proxy)).flush()
            return True
        return False

    def save_proxy_to_file(self):
        with open(self.data_path, 'wb') as f:
            pickle.dump(self.last_proxy, f)

    def get_proxy_from_file(self):
        return self.proxy_list[random.randint(0, len(self.proxy_list) - 1)]

    def read_proxies(self):
        proxy_path = os.path.join(os.path.dirname(__file__), './proxy_list')
        try:
            with open(proxy_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for i in lines:
                    p = i.strip("\n")
                    self.proxy_list.append(p)
        except Exception:
            with open(proxy_path, "r", ) as f:
                lines = f.readlines()
                for i in lines:
                    p = i.strip("\n")
                    self.proxy_list.append(p)
        return self.proxy_list

    def check_proxies_available(self):
        if Config().PROXY_ENABLE and Config().PROXY_TYPE == 1:
            try:
                res = requests.get(API_PROXY_STATUS.format(Config().PROXY_API_IP, Config().PROXY_API_PORT))
                self.proxy_num = res.json()['useful_proxy']
            except Exception:
                ProxyLog.api_not_connect()
        elif Config().PROXY_ENABLE and Config().PROXY_TYPE == 2:
            self.proxy_num = len(self.proxy_list)
        if self.proxy_num is 0:
            return False
        return True

    def delete_proxy(self):
        if not Config().PROXY_ENABLE or self.last_proxy not in self.proxy_list:
            return
        if Config().PROXY_TYPE == 1:
            try:
                requests.get(API_PROXY_DELETE.format(Config().PROXY_API_IP, Config().PROXY_API_PORT, self.last_proxy))
            except Exception:
                ProxyLog.api_not_connect()
                Config().PROXY_ENABLE = 0
        elif Config().PROXY_TYPE == 2:
            self.proxy_list.remove(self.last_proxy)
        ProxyLog.delete_proxy(self.last_proxy)

    @classmethod
    def get_proxy(cls):
        self = cls()
        proxies = None
        if Config().PROXY_ENABLE and self.last_proxy is not None:
            proxies = {
                'http': 'http://{}'.format(self.last_proxy),
                'https': 'http://{}'.format(self.last_proxy),
            }
            # ProxyLog.use_proxy(self.last_proxy)
        return proxies

    @classmethod
    def get_proxy_ip(cls):
        self = cls()
        return self.last_proxy

    @classmethod
    def update_proxy(cls, timeout=False):
        # TODO - 请求未出错，但是状态码不对，需要手动调用该方法
        # ProxyLog.add_quick_log('update proxy ').flush()
        self = cls()
        self.wrong_time += 1
        if Config().PROXY_ENABLE and (timeout or self.wrong_time > 3):  # 错误次数达到3次以后，更换ip
            self.delete_proxy()
            self.load_proxy()
            self.wrong_time = 0

    @classmethod
    def get_timeout(cls):
        return Config().PROXY_TIME_OUT
