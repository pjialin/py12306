import urllib

from py12306.config import Config
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

    @classmethod
    def send_email(cls, to, title='', content=''):
        self = cls()
        self.send_email_by_smtp(to, title, content)

    def send_voice_code_of_yiyuan(self, phone, name='', content=''):
        """
        发送语音验证码
        购买地址 https://market.aliyun.com/products/57126001/cmapi019902.html?spm=5176.2020520132.101.5.37857218O6iJ3n
        :return:
        """
        appcode = Config().NOTIFICATION_API_APP_CODE
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
        result = response.json()
        response_message = result.get('showapi_res_body.remark')
        if response.status_code in [400, 401, 403]:
            return CommonLog.add_quick_log(CommonLog.MESSAGE_VOICE_API_FORBID).flush()
        if response.status_code == 200 and result.get('showapi_res_body.flag'):
            CommonLog.add_quick_log(CommonLog.MESSAGE_VOICE_API_SEND_SUCCESS.format(response_message)).flush()
            return True
        else:
            return CommonLog.add_quick_log(CommonLog.MESSAGE_VOICE_API_SEND_FAIL.format(response_message)).flush()

    def send_email_by_smtp(self, to, title, content):
        import smtplib
        from email.message import EmailMessage
        to = to if isinstance(to, list) else [to]
        message = EmailMessage()
        message['Subject'] = title
        message['From'] = 'service@pjialin.com'
        message['To'] = to
        message.set_content(content)
        try:
            server = smtplib.SMTP(Config().EMAIL_SERVER_HOST)
            server.login(Config().EMAIL_SERVER_USER, Config().EMAIL_SERVER_PASSWORD)
            server.send_message(message)
            server.quit()
            CommonLog.add_quick_log(CommonLog.MESSAGE_SEND_EMAIL_SUCCESS).flush()
        except Exception as e:
            CommonLog.add_quick_log(CommonLog.MESSAGE_SEND_EMAIL_FAIL.format(e)).flush()


if __name__ == '__main__':
    name = '张三3'
    content = '你的车票 广州 到 深圳 购买成功，请登录 12306 进行支付'
    # Notification.voice_code('13800138000', name, content)
    Notification.send_email('admin@pjialin.com', name, content)
