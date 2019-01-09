import urllib

from py12306.helpers.api import *
from py12306.helpers.request import Request
from py12306.log.common_log import CommonLog


class Notification():
    """
    通知类
    """
    session = None

    def __init__(self):
        self.session = Request()

    @classmethod
    def voice_code(cls, phone, name='', content=''):
        self = cls()
        self.send_voice_code_of_yiyuan(phone, name=name, content=content)

    def send_voice_code_of_yiyuan(self, phone, name='', content=''):
        """
        发送语音验证码
        购买地址 https://market.aliyun.com/products/57126001/cmapi019902.html?spm=5176.2020520132.101.5.37857218O6iJ3n
        :return:
        """
        appcode = config.NOTIFICATION_API_APP_CODE
        if not appcode:
            CommonLog.add_quick_log(CommonLog.MESSAGE_EMPTY_APP_CODE).flush()
            return False
        body = {
            'userName': name,
            'mailNo': content
        }
        params = {
            'content': body,
            'mobile': phone,
            'sex': 2,
            'tNum': 'T170701001056'
        }
        response = self.session.request(url=API_NOTIFICATION_BY_VOICE_CODE + urllib.parse.urlencode(params),
                                        method='GET', headers={
                'Authorization': 'APPCODE {}'.format(appcode)
            })
        response_message = '-'
        result = {}
        try:
            result = response.json()
            response_message = result['showapi_res_body']['remark']
        except:
            pass
        if response.status_code == 401 or response.status_code == 403:
            return CommonLog.add_quick_log(CommonLog.MESSAGE_VOICE_API_FORBID).flush()
        if response.status_code == 200 and 'showapi_res_body' in result and result['showapi_res_body'].get('flag'):
            CommonLog.add_quick_log(CommonLog.MESSAGE_VOICE_API_SEND_SUCCESS.format(response_message)).flush()
            return True
        else:
            return CommonLog.add_quick_log(CommonLog.MESSAGE_VOICE_API_SEND_FAIL.format(response_message)).flush()


if __name__ == '__main__':
    Notification.voice_code('13800138000', '张三', '你的车票 广州 到 深圳 购买成功，请登录 12306 进行支付')
