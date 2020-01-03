import random
import time

from requests.exceptions import SSLError

from py12306.config import Config
from py12306.helpers.OCR import OCR
from py12306.helpers.api import *
from py12306.helpers.request import Request
from py12306.helpers.func import *
from py12306.log.common_log import CommonLog
from py12306.log.user_log import UserLog


class AuthCode:
    """
    验证码类
    """
    session = None
    data_path = None
    retry_time = 5

    def __init__(self, session):
        self.data_path = Config().RUNTIME_DIR
        self.session = session

    @classmethod
    def get_auth_code(cls, session):
        self = cls(session)
        img = self.download_code()
        position = OCR.get_img_position(img)
        if not position:  # 打码失败
            return self.retry_get_auth_code()

        answer = ','.join(map(str, position))

        if not self.check_code(answer):
            return self.retry_get_auth_code()
        return position

    def retry_get_auth_code(self): # TODO 安全次数检测
        CommonLog.add_quick_log(CommonLog.MESSAGE_RETRY_AUTH_CODE.format(self.retry_time)).flush()
        time.sleep(self.retry_time)
        return self.get_auth_code(self.session)

    def download_code(self):
        url = API_AUTH_CODE_BASE64_DOWNLOAD.format(random=random.random())
        # code_path = self.data_path + 'code.png'
        try:
            self.session.cookies.clear_session_cookies()
            UserLog.add_quick_log(UserLog.MESSAGE_DOWNLAODING_THE_CODE).flush()
            # response = self.session.save_to_file(url, code_path)  # TODO 返回错误情况
            response = self.session.get(url)
            result = response.json()
            if result.get('image'):
                return result.get('image')
            raise SSLError('返回数据为空')
        except SSLError as e:
            UserLog.add_quick_log(
                UserLog.MESSAGE_DOWNLAOD_AUTH_CODE_FAIL.format(e, self.retry_time)).flush()
            time.sleep(self.retry_time)
            return self.download_code()

    def check_code(self, answer):
        """
        校验验证码
        :return:
        """
        url = API_AUTH_CODE_CHECK.get('url').format(answer=answer, random=time_int())
        response = self.session.get(url)
        result = response.json()
        if result.get('result_code') == '4':
            UserLog.add_quick_log(UserLog.MESSAGE_CODE_AUTH_SUCCESS).flush()
            return True
        else:
            # {'result_message': '验证码校验失败', 'result_code': '5'}
            UserLog.add_quick_log(
                UserLog.MESSAGE_CODE_AUTH_FAIL.format(result.get('result_message'))).flush()
            self.session.cookies.clear_session_cookies()

        return False


if __name__ == '__main__':
    code_result = AuthCode.get_auth_code()
