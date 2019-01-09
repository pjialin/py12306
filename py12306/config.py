import json
import re
from os import path

# 12306 账号
from py12306.helpers.func import *


@singleton
class Config:
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

    STATION_FILE = PROJECT_DIR + 'data/stations.txt'
    CONFIG_FILE = PROJECT_DIR + 'env.py'

    # 语音验证码
    NOTIFICATION_BY_VOICE_CODE = 0
    NOTIFICATION_VOICE_CODE_PHONE = ''
    NOTIFICATION_API_APP_CODE = ''

    # 集群配置
    CLUSTER_ENABLED = 1
    NODE_IS_MASTER = 1
    NODE_NAME = ''
    REDIS_HOST = ''
    REDIS_PORT = '6379'
    REDIS_PASSWORD = ''

    envs = []
    retry_time = 5

    @classmethod
    def run(cls):
        self = cls()
        self.start()

    # @classmethod
    # def keep_work(cls):
    #     self = cls()

    def start(self):
        self.init_envs()
        self.save_to_remote()
        # self.refresh_configs()
        create_thread_and_run(self, 'refresh_configs', wait=False)

    def refresh_configs(self):
        if not self.is_cluster_enabled(): return
        while True:
            remote_configs = self.get_remote_config()
            self.update_configs_from_remote(remote_configs)
            stay_second(self.retry_time)

    def get_remote_config(self):
        if not self.is_cluster_enabled(): return
        from py12306.cluster.cluster import Distributed
        return Distributed().session.get_pickle(Distributed().KEY_CONFIGS, {})

    def save_to_remote(self):
        if not self.is_master(): return
        from py12306.cluster.cluster import Distributed
        Distributed().session.set_pickle(Distributed().KEY_CONFIGS, self.envs)

    def init_envs(self):
        self.envs = EnvLoader.load_with_file(self.CONFIG_FILE)
        self.update_configs(self.envs)

    def update_configs(self, envs):
        for key, value in envs:
            setattr(self, key, value)

    def update_configs_from_remote(self, envs):
        if envs == self.envs: return
        from py12306.query.query import Query
        for key, value in envs:
            if key == 'USER_ACCOUNTS' and value != self.USER_ACCOUNTS:  # 用户修改
                setattr(self, key, value)
                print('用户修改了') # TODO
            elif key == 'QUERY_JOBS' and value != self.QUERY_JOBS:  # 任务修改
                setattr(self, key, value) and Query().update_query_jobs(auto=True)
            elif key == 'QUERY_INTERVAL' and value != self.QUERY_INTERVAL:  # 任务修改
                setattr(self, key, value) and Query().update_query_interval(auto=True)
            if value != -1:
                setattr(self, key, value)

    @staticmethod
    def is_master():  # 是不是 主
        return Config.CLUSTER_ENABLED and Config.NODE_IS_MASTER

    @staticmethod
    def is_slave():  # 是不是 从
        return Config.CLUSTER_ENABLED and not Config.NODE_IS_MASTER

    @staticmethod
    def is_cluster_enabled():
        return Config.CLUSTER_ENABLED

    # @staticmethod
    # def get_members():
    #     members = []
    #     for name, value in vars(Config).items():
    #         if name.isupper():
    #             members.append(([name, value]))
    #     return members


class EnvLoader():
    envs = []

    @classmethod
    def load_with_file(cls, file):
        self = cls()
        if path.exists(file):
            env_content = open(file, encoding='utf8').read()
            content = re.sub(r'^([A-Z]+)_', r'self.\1_', env_content, flags=re.M)
            exec(content)
        return self.envs

    def __setattr__(self, key, value):
        self.envs.append(([key, value]))
