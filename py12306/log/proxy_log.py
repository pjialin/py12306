from py12306.log.base import BaseLog
from py12306.helpers.func import *


@singleton
class ProxyLog(BaseLog):
    # 这里如果不声明，会出现重复打印，目前不知道什么原因
    logs = []
    thread_logs = {}
    quick_log = []

    MESSAGE_API_SERVER_NOT_CONNECT = '无法通过API获取代理IP，请检查是否服务是否开启。\n'
    MESSAGE_PROXY_GET = '使用代理IP: {}\n'
    MESSAGE_PROXY_UNABLE = '代理IP: {} 不可用，删除'
    MESSAGE_PROXY_UNAVAILABLE = '可用代理IP列表为空，请检查，将禁用代理功能。\n'

    def __init__(self):
        super().__init__()
        self.init_data()

    def init_data(self):
        pass

    @classmethod
    def api_not_connect(cls):
        self = cls()
        self.add_quick_log(self.MESSAGE_API_SERVER_NOT_CONNECT)
        self.flush()
        return self

    @classmethod
    def use_proxy(cls, proxy_ip):
        self = cls()
        self.add_quick_log(self.MESSAGE_PROXY_GET.format(proxy_ip))
        self.flush()
        return self

    @classmethod
    def delete_proxy(cls, proxy_ip):
        self = cls()
        self.add_quick_log(self.MESSAGE_PROXY_UNABLE.format(proxy_ip))
        self.flush()
        return self

    @classmethod
    def proxy_unavailable(cls):
        self = cls()
        self.add_quick_log(self.MESSAGE_PROXY_UNAVAILABLE)
        self.flush()
        return self
