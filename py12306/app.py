# -*- coding: utf-8 -*-
import os
import signal
import sys

from py12306.helpers.func import *
from py12306.config import Config
from py12306.helpers.notification import Notification
from py12306.log.common_log import CommonLog
from py12306.log.order_log import OrderLog


def app_available_check():
    # return True  # Debug
    if Config().IS_DEBUG:
        return True
    now = time_now()
    if now.hour >= 23 or now.hour < 6:
        CommonLog.add_quick_log(CommonLog.MESSAGE_12306_IS_CLOSED.format(time_now())).flush()
        open_time = datetime.datetime(now.year, now.month, now.day, 6)
        if open_time < now:
            open_time += datetime.timedelta(1)
        sleep((open_time - now).seconds)
    return True


@singleton
class App:
    """
    程序主类
    TODO 代码需要优化
    """

    @classmethod
    def run(cls):
        self = cls()
        self.register_sign()
        self.start()

    def start(self):
        Config().run()
        self.init_class()

    @classmethod
    def did_start(cls):
        self = cls()
        from py12306.helpers.station import Station
        Station()  # 防止多线程时初始化出现问题
        # if Config.is_cluster_enabled():
        #     from py12306.cluster.cluster import Cluster
        #     Cluster().run()

    def init_class(self):
        from py12306.cluster.cluster import Cluster
        if Config.is_cluster_enabled():
            Cluster().run()

    def register_sign(self):
        is_windows = os.name == 'nt'
        # if is_windows:
        signs = [signal.SIGINT, signal.SIGTERM]
        # else:
        #     signs = [signal.SIGINT, signal.SIGHUP, signal.SIGTERM] # SIGHUP 会导致终端退出，程序也退出，暂时去掉
        for sign in signs:
            signal.signal(sign, self.handler_exit)

        pass

    def handler_exit(self, *args, **kwargs):
        """
        程序退出
        :param args:
        :param kwargs:
        :return:
        """
        if Config.is_cluster_enabled():
            from py12306.cluster.cluster import Cluster
            Cluster().left_cluster()

        sys.exit()

    @classmethod
    def check_auto_code(cls):
        if Config().AUTO_CODE_PLATFORM == 'free': return True
        if not Config().AUTO_CODE_ACCOUNT.get('user') or not Config().AUTO_CODE_ACCOUNT.get('pwd'):
            return False
        return True

    @classmethod
    def check_user_account_is_empty(cls):
        if Config().USER_ACCOUNTS:
            for account in Config().USER_ACCOUNTS:
                if account:
                    return False
        return True

    @staticmethod
    def check_data_dir_exists():
        os.makedirs(Config().QUERY_DATA_DIR, exist_ok=True)
        os.makedirs(Config().USER_DATA_DIR, exist_ok=True)
        touch_file(Config().OUT_PUT_LOG_TO_FILE_PATH)

    @classmethod
    def test_send_notifications(cls):
        if Config().NOTIFICATION_BY_VOICE_CODE:  # 语音通知
            CommonLog.add_quick_log(CommonLog.MESSAGE_TEST_SEND_VOICE_CODE).flush()
            if Config().NOTIFICATION_VOICE_CODE_TYPE == 'dingxin':
                voice_content = {'left_station': '广州', 'arrive_station': '深圳', 'set_type': '硬座', 'orderno': 'E123542'}
            else:
                voice_content = OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_OF_VOICE_CODE_CONTENT.format('北京',
                                                                                                         '深圳')
            Notification.voice_code(Config().NOTIFICATION_VOICE_CODE_PHONE, '张三', voice_content)
        if Config().EMAIL_ENABLED:  # 邮件通知
            CommonLog.add_quick_log(CommonLog.MESSAGE_TEST_SEND_EMAIL).flush()
            Notification.send_email(Config().EMAIL_RECEIVER, '测试发送邮件', 'By py12306')

        if Config().DINGTALK_ENABLED:  # 钉钉通知
            CommonLog.add_quick_log(CommonLog.MESSAGE_TEST_SEND_DINGTALK).flush()
            Notification.dingtalk_webhook('测试发送信息')

        if Config().TELEGRAM_ENABLED:  # Telegram通知
            CommonLog.add_quick_log(CommonLog.MESSAGE_TEST_SEND_TELEGRAM).flush()
            Notification.send_to_telegram('测试发送信息')

        if Config().SERVERCHAN_ENABLED:  # ServerChan通知
            CommonLog.add_quick_log(CommonLog.MESSAGE_TEST_SEND_SERVER_CHAN).flush()
            Notification.server_chan(Config().SERVERCHAN_KEY, '测试发送消息', 'By py12306')

        if Config().PUSHBEAR_ENABLED:  # PushBear通知
            CommonLog.add_quick_log(CommonLog.MESSAGE_TEST_SEND_PUSH_BEAR).flush()
            Notification.push_bear(Config().PUSHBEAR_KEY, '测试发送消息', 'By py12306')

    @classmethod
    def run_check(cls):
        """
        待优化
        :return:
        """
        cls.check_data_dir_exists()
        if not cls.check_user_account_is_empty():
            # CommonLog.add_quick_log(CommonLog.MESSAGE_CHECK_EMPTY_USER_ACCOUNT).flush(exit=True, publish=False) # 不填写用户则不自动下单
            if not cls.check_auto_code():
                CommonLog.add_quick_log(CommonLog.MESSAGE_CHECK_AUTO_CODE_FAIL).flush(exit=True, publish=False)
        if Const.IS_TEST_NOTIFICATION: cls.test_send_notifications()


# Expand
class Dict(dict):
    def get(self, key, default=None, sep='.'):
        keys = key.split(sep)
        for i, key in enumerate(keys):
            try:
                value = self[key]
                if len(keys[i + 1:]) and isinstance(value, Dict):
                    return value.get(sep.join(keys[i + 1:]), default=default, sep=sep)
                return value
            except:
                return self.dict_to_dict(default)

    def __getitem__(self, k):
        return self.dict_to_dict(super().__getitem__(k))

    @staticmethod
    def dict_to_dict(value):
        return Dict(value) if isinstance(value, dict) else value
