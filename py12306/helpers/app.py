from py12306.helpers.func import *
from py12306.config import *
from py12306.helpers.notification import Notification
from py12306.log.common_log import CommonLog
from py12306.log.order_log import OrderLog


def app_available_check():
    # return True  # Debug
    now = time_now()
    if now.hour >= 23 or now.hour < 6:
        CommonLog.add_quick_log(CommonLog.MESSAGE_12306_IS_CLOSED.format(time_now())).flush()
        open_time = datetime.datetime(now.year, now.month, now.day, 6)
        if open_time < now:
            open_time += datetime.timedelta(1)
        sleep((open_time - now).seconds)
    return True


class App:
    """
    程序主类
    TODO 需要完善
    """

    @classmethod
    def check_auto_code(cls):
        if not config.AUTO_CODE_ACCOUNT.get('user') or not config.AUTO_CODE_ACCOUNT.get('pwd'):
            return False
        return True

    @classmethod
    def check_user_account_is_empty(cls):
        if config.USER_ACCOUNTS:
            for account in config.USER_ACCOUNTS:
                if account:
                    return True
        return False

    @classmethod
    def test_send_notifications(cls):
        if config.NOTIFICATION_BY_VOICE_CODE:  # 语音通知
            CommonLog.add_quick_log(CommonLog.MESSAGE_TEST_SEND_VOICE_CODE).flush()
            Notification.voice_code(config.NOTIFICATION_VOICE_CODE_PHONE, '张三',
                                    OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_OF_VOICE_CODE_CONTENT.format('北京',
                                                                                                             '深圳'))

    @classmethod
    def run_check(cls):
        """
        待优化
        :return:
        """
        if not cls.check_auto_code():
            CommonLog.add_quick_log(CommonLog.MESSAGE_CHECK_AUTO_CODE_FAIL).flush(exit=True)
        if not cls.check_user_account_is_empty():
            CommonLog.add_quick_log(CommonLog.MESSAGE_CHECK_EMPTY_USER_ACCOUNT).flush(exit=True)
        if Const.IS_TEST_NOTIFICATION: cls.test_send_notifications()
