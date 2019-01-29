# -*- coding: utf-8 -*-
import json
import re
from os import path

# 12306 账号
from py12306.helpers.func import *


@singleton
class Config:
    IS_DEBUG = False

    USER_ACCOUNTS = []
    # 查询任务
    QUERY_JOBS = []
    # 查询间隔
    QUERY_INTERVAL = 1
    # 用户心跳检测间隔
    USER_HEARTBEAT_INTERVAL = 120
    # 多线程查询
    QUERY_JOB_THREAD_ENABLED = 0
    # 打码平台账号
    AUTO_CODE_PLATFORM = ''
    AUTO_CODE_ACCOUNT = {'user': '', 'pwd': ''}
    # 输出日志到文件
    OUT_PUT_LOG_TO_FILE_ENABLED = 0
    OUT_PUT_LOG_TO_FILE_PATH = 'runtime/12306.log'

    SEAT_TYPES = {'特等座': 25, '商务座': 32, '一等座': 31, '二等座': 30, '软卧': 23, '硬卧': 28, '硬座': 29, '无座': 26, }

    ORDER_SEAT_TYPES = {'特等座': 'P', '商务座': 9, '一等座': 'M', '二等座': 'O', '软卧': 4, '硬卧': 3, '硬座': 1, '无座': 1}

    PROJECT_DIR = path.dirname(path.dirname(path.abspath(__file__))) + '/'

    # Query
    RUNTIME_DIR = PROJECT_DIR + 'runtime/'
    QUERY_DATA_DIR = RUNTIME_DIR + 'query/'
    USER_DATA_DIR = RUNTIME_DIR + 'user/'
    USER_PASSENGERS_FILE = RUNTIME_DIR + 'user/%s_passengers.json'

    STATION_FILE = PROJECT_DIR + 'data/stations.txt'
    CONFIG_FILE = PROJECT_DIR + 'env.py'

    # 语音验证码
    NOTIFICATION_BY_VOICE_CODE = 0
    NOTIFICATION_VOICE_CODE_TYPE = ''
    NOTIFICATION_VOICE_CODE_PHONE = ''
    NOTIFICATION_API_APP_CODE = ''

    # 集群配置
    CLUSTER_ENABLED = 0
    NODE_SLAVE_CAN_BE_MASTER = 1
    NODE_IS_MASTER = 1
    NODE_NAME = ''
    REDIS_HOST = ''
    REDIS_PORT = '6379'
    REDIS_PASSWORD = ''

    # 钉钉配置
    DINGTALK_ENABLED = 0
    DINGTALK_WEBHOOK = ''

    # Telegram推送配置
    TELEGRAM_ENABLED = 0
    TELEGRAM_BOT_API_URL = ''

    # ServerChan和PushBear配置
    SERVERCHAN_ENABLED = 0
    SERVERCHAN_KEY = '8474-ca071ADSFADSF'
    PUSHBEAR_ENABLED = 0
    PUSHBEAR_KEY = 'SCUdafadsfasfdafdf45234234234'

    # 邮箱配置
    EMAIL_ENABLED = 0
    EMAIL_SENDER = ''
    EMAIL_RECEIVER = ''
    EMAIL_SERVER_HOST = ''
    EMAIL_SERVER_USER = ''
    EMAIL_SERVER_PASSWORD = ''

    WEB_ENABLE = 0
    WEB_USER = {}
    WEB_PORT = 8080
    WEB_ENTER_HTML_PATH = PROJECT_DIR + 'py12306/web/static/index.html'

    # CDN
    CDN_ENABLED = 0
    CDN_CHECK_TIME_OUT = 2
    CDN_ITEM_FILE = PROJECT_DIR + 'data/cdn.txt'
    CDN_ENABLED_AVAILABLE_ITEM_FILE = QUERY_DATA_DIR + 'available.json'

    # Default time out
    TIME_OUT_OF_REQUEST = 5

    envs = []
    retry_time = 5
    last_modify_time = 0

    disallow_update_configs = [
        'CLUSTER_ENABLED',
        'NODE_IS_MASTER',
        'NODE_NAME',
        'REDIS_HOST',
        'REDIS_PORT',
        'REDIS_PASSWORD',
    ]

    def __init__(self):
        self.init_envs()
        self.last_modify_time = get_file_modify_time(self.CONFIG_FILE)
        if Config().is_slave():
            self.refresh_configs(True)
        else:
            create_thread_and_run(self, 'watch_file_change', False)

    @classmethod
    def run(cls):
        self = cls()
        self.start()

    # @classmethod
    # def keep_work(cls):
    #     self = cls()

    def start(self):
        self.save_to_remote()
        create_thread_and_run(self, 'refresh_configs', wait=Const.IS_TEST)

    def refresh_configs(self, once=False):
        if not self.is_cluster_enabled(): return
        while True:
            remote_configs = self.get_remote_config()
            self.update_configs_from_remote(remote_configs, once)
            if once or Const.IS_TEST: return
            stay_second(self.retry_time)

    def get_remote_config(self):
        if not self.is_cluster_enabled(): return
        from py12306.cluster.cluster import Cluster
        return Cluster().session.get_pickle(Cluster().KEY_CONFIGS, {})

    def save_to_remote(self):
        if not self.is_master(): return
        from py12306.cluster.cluster import Cluster
        Cluster().session.set_pickle(Cluster().KEY_CONFIGS, self.envs)

    def init_envs(self):
        self.envs = EnvLoader.load_with_file(self.CONFIG_FILE)
        self.update_configs(self.envs)

    def update_configs(self, envs):
        for key, value in envs:
            setattr(self, key, value)

    def watch_file_change(self):
        """
        监听配置文件修改
        :return:
        """
        if Config().is_slave(): return
        from py12306.log.common_log import CommonLog
        while True:
            value = get_file_modify_time(self.CONFIG_FILE)
            if value > self.last_modify_time:
                self.last_modify_time = value
                CommonLog.add_quick_log(CommonLog.MESSAGE_CONFIG_FILE_DID_CHANGED).flush()
                envs = EnvLoader.load_with_file(self.CONFIG_FILE)
                self.update_configs_from_remote(envs)
                if Config().is_master():  # 保存配置
                    self.save_to_remote()
            stay_second(self.retry_time)

    def update_configs_from_remote(self, envs, first=False):
        if envs == self.envs: return
        from py12306.query.query import Query
        from py12306.user.user import User
        from py12306.helpers.cdn import Cdn
        self.envs = envs
        for key, value in envs:
            if key in self.disallow_update_configs: continue
            if value != -1:
                old = getattr(self, key)
                setattr(self, key, value)
                if not first and old != value:
                    if key == 'USER_ACCOUNTS':
                        User().update_user_accounts(auto=True, old=old)
                    elif key == 'QUERY_JOBS':
                        Query().update_query_jobs(auto=True)  # 任务修改
                    elif key == 'QUERY_INTERVAL':
                        Query().update_query_interval(auto=True)
                    elif key == 'CDN_ENABLED':
                        Cdn().update_cdn_status(auto=True)

    @staticmethod
    def is_master():  # 是不是 主
        from py12306.cluster.cluster import Cluster
        return Config().CLUSTER_ENABLED and (Config().NODE_IS_MASTER or Cluster().is_master)

    @staticmethod
    def is_slave():  # 是不是 从
        return Config().CLUSTER_ENABLED and not Config.is_master()

    @staticmethod
    def is_cluster_enabled():
        return Config().CLUSTER_ENABLED

    @staticmethod
    def is_cdn_enabled():
        return Config().CDN_ENABLED


class EnvLoader:
    envs = []

    def __init__(self):
        self.envs = []

    @classmethod
    def load_with_file(cls, file):
        self = cls()
        if path.exists(file):
            env_content = open(file, encoding='utf8').read()
            content = re.sub(r'^([A-Z]+)_', r'self.\1_', env_content, flags=re.M)
            exec(content)
        return self.envs

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if re.search(r'^[A-Z]+_', key):
            self.envs.append(([key, value]))
