# encoding=utf8
import sys

from py12306.app import *
from py12306.log.common_log import CommonLog
from py12306.query.query import Query


def main():
    if '--test' in sys.argv or '-t' in sys.argv: test()
    App.run()
    CommonLog.print_welcome().print_configs()
    App.did_start()
    # App.run_check()
    # User.run()
    Query.run()
    if not Const.IS_TEST:
        while True:
            sleep(10000)

    CommonLog.print_test_complete()


def test():
    """
    功能检查
    包含：
        账号密码验证 (打码)
        座位验证
        乘客验证
        语音验证码验证
    :return:
    """
    Const.IS_TEST = True
    Config.OUT_PUT_LOG_TO_FILE_ENABLED = False
    if '--test-notification' in sys.argv or '-n' in sys.argv:
        Const.IS_TEST_NOTIFICATION = True
    pass


if __name__ == '__main__':
    main()
