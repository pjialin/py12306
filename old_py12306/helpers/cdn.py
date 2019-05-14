import random
import json
from datetime import timedelta
from os import path

from py12306.cluster.cluster import Cluster
from py12306.config import Config
from py12306.app import app_available_check
from py12306.helpers.api import API_CHECK_CDN_AVAILABLE, HOST_URL_OF_12306
from py12306.helpers.func import *
from py12306.helpers.request import Request
from py12306.log.common_log import CommonLog


@singleton
class Cdn:
    """
    CDN 管理
    """
    items = []
    available_items = []
    unavailable_items = []
    recheck_available_items = []
    recheck_unavailable_items = []
    retry_time = 3
    is_ready = False
    is_finished = False
    is_ready_num = 10  # 当可用超过 10，已准备好
    is_alive = True
    is_recheck = False

    safe_stay_time = 0.2
    retry_num = 1
    thread_num = 5
    check_time_out = 3

    last_check_at = 0
    save_second = 5
    check_keep_second = 60 * 60 * 24

    def __init__(self):
        self.cluster = Cluster()
        self.init_config()
        create_thread_and_run(self, 'watch_cdn', False)

    def init_data(self):
        self.items = []
        self.available_items = []
        self.unavailable_items = []
        self.is_finished = False
        self.is_ready = False
        self.is_recheck = False

    def init_config(self):
        self.check_time_out = Config().CDN_CHECK_TIME_OUT

    def update_cdn_status(self, auto=False):
        if auto:
            self.init_config()
            if Config().is_cdn_enabled():
                self.run()
            else:
                self.destroy()

    @classmethod
    def run(cls):
        self = cls()
        app_available_check()
        self.is_alive = True
        self.start()
        pass

    def start(self):
        if not Config.is_cdn_enabled(): return
        self.load_items()
        CommonLog.add_quick_log(CommonLog.MESSAGE_CDN_START_TO_CHECK.format(len(self.items))).flush()
        self.restore_items()
        for i in range(self.thread_num):  # 多线程
            create_thread_and_run(jobs=self, callback_name='check_available', wait=False)

    def load_items(self):
        with open(Config().CDN_ITEM_FILE, encoding='utf-8') as f:
            for line, val in enumerate(f):
                self.items.append(val.rstrip('\n'))

    def restore_items(self):
        """
        恢复已有数据
        :return: bool
        """
        result = False
        if path.exists(Config().CDN_ENABLED_AVAILABLE_ITEM_FILE):
            with open(Config().CDN_ENABLED_AVAILABLE_ITEM_FILE, encoding='utf-8') as f:
                result = f.read()
                try:
                    result = json.loads(result)
                except json.JSONDecodeError as e:
                    result = {}

        # if Config.is_cluster_enabled(): # 集群不用同步 cdn
        #     result = self.get_data_from_cluster()

        if result:
            self.last_check_at = result.get('last_check_at', '')
            if self.last_check_at: self.last_check_at = str_to_time(self.last_check_at)
            self.available_items = result.get('items', [])
            self.unavailable_items = result.get('fail_items', [])
            CommonLog.add_quick_log(CommonLog.MESSAGE_CDN_RESTORE_SUCCESS.format(self.last_check_at)).flush()
            return True
        return False

    # def get_data_from_cluster(self):
    #     available_items = self.cluster.session.smembers(Cluster.KEY_CDN_AVAILABLE_ITEMS)
    #     last_time = self.cluster.session.get(Cluster.KEY_CDN_LAST_CHECK_AT, '')
    #     if available_items and last_time:
    #         return {'items': available_items, 'last_check_at': last_time}
    #     return False

    def is_need_to_recheck(self):
        """
        是否需要重新检查 cdn
        :return:
        """
        if self.last_check_at and (
                time_now() - self.last_check_at).seconds > self.check_keep_second:
            return True
        return False

    def get_unchecked_item(self):
        if not self.is_recheck:
            items = list(set(self.items) - set(self.available_items) - set(self.unavailable_items))
        else:
            items = list(set(self.items) - set(self.recheck_available_items) - set(self.recheck_unavailable_items))
        if items: return random.choice(items)
        return None

    def check_available(self):
        while True and self.is_alive:
            item = self.get_unchecked_item()
            if not item: return self.check_did_finished()
            self.check_item_available(item)

    def watch_cdn(self):
        """
        监控 cdn 状态，自动重新检测
        :return:
        """
        while True:
            if self.is_alive and not self.is_recheck and self.is_need_to_recheck():  # 重新检测
                self.is_recheck = True
                self.is_finished = False
                CommonLog.add_quick_log(
                    CommonLog.MESSAGE_CDN_START_TO_RECHECK.format(len(self.items), time_now())).flush()
                for i in range(self.thread_num):  # 多线程
                    create_thread_and_run(jobs=self, callback_name='check_available', wait=False)
            stay_second(self.retry_num)

    def destroy(self):
        """
        关闭 CDN
        :return:
        """
        CommonLog.add_quick_log(CommonLog.MESSAGE_CDN_CLOSED).flush()
        self.is_alive = False
        self.init_data()

    def check_item_available(self, item, try_num=0):
        session = Request()
        response = session.get(API_CHECK_CDN_AVAILABLE.format(item), headers={'Host': HOST_URL_OF_12306},
                               timeout=self.check_time_out,
                               verify=False)

        if response.status_code == 200:
            if not self.is_recheck:
                self.available_items.append(item)
            else:
                self.recheck_available_items.append(item)
            if not self.is_ready: self.check_is_ready()
        elif try_num < self.retry_num:  # 重试
            stay_second(self.safe_stay_time)
            return self.check_item_available(item, try_num + 1)
        else:
            if not self.is_recheck:
                self.unavailable_items.append(item)
            else:
                self.recheck_unavailable_items.append(item)
        if not self.is_recheck and (
                not self.last_check_at or (time_now() - self.last_check_at).seconds > self.save_second):
            self.save_available_items()
        stay_second(self.safe_stay_time)

    def check_did_finished(self):
        self.is_ready = True
        if not self.is_finished:
            self.is_finished = True
            if self.is_recheck:
                self.is_recheck = False
                self.available_items = self.recheck_available_items
                self.unavailable_items = self.recheck_unavailable_items
                self.recheck_available_items = []
                self.recheck_unavailable_items = []
            CommonLog.add_quick_log(CommonLog.MESSAGE_CDN_CHECKED_SUCCESS.format(len(self.available_items))).flush()
            self.save_available_items()

    def save_available_items(self):
        self.last_check_at = time_now()
        data = {'items': self.available_items, 'fail_items': self.unavailable_items,
                'last_check_at': str(self.last_check_at)}
        with open(Config().CDN_ENABLED_AVAILABLE_ITEM_FILE, 'w') as f:
            f.write(json.dumps(data))

        # if Config.is_master():
        #     self.cluster.session.sadd(Cluster.KEY_CDN_AVAILABLE_ITEMS, self.available_items)
        #     self.cluster.session.set(Cluster.KEY_CDN_LAST_CHECK_AT, time_now())

    def check_is_ready(self):
        if len(self.available_items) > self.is_ready_num:
            self.is_ready = True
        else:
            self.is_ready = False

    @classmethod
    def get_cdn(cls):
        self = cls()
        if self.is_ready and self.available_items:
            return random.choice(self.available_items)
        return None


if __name__ == '__main__':
    # Const.IS_TEST = True
    Cdn.run()
    while not Cdn().is_finished:
        stay_second(1)
