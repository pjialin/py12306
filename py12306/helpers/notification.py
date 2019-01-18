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
        if Config().NOTIFICATION_VOICE_CODE_TYPE == 'dingxin':
            self.send_voice_code_of_dingxin(phone, name=name, info=content)
        else:
            self.send_voice_code_of_yiyuan(phone, name=name, content=content)

    @classmethod
    def dingtalk_webhook(cls, content=''):
        self = cls()
        self.send_dingtalk_by_webbook(content=content)

    @classmethod
    def send_email(cls, to, title='', content=''):
        self = cls()
        self.send_email_by_smtp(to, title, content)

    @classmethod
    def send_to_telegram(cls, content=''):
        self = cls()
        self.send_to_telegram_bot(content=content)

    @classmethod
    def server_chan(cls, skey='', title='', content=''):
        self = cls()
        self.send_serverchan(skey=skey, title=title, content=content)

    @classmethod
    def push_bear(cls, skey='', title='', content=''):
        self = cls()
        self.send_pushbear(skey=skey, title=title, content=content)

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
                                        method='GET', headers={'Authorization': 'APPCODE {}'.format(appcode)})
        result = response.json()
        response_message = result.get('showapi_res_body.remark')
        if response.status_code in [400, 401, 403]:
            return CommonLog.add_quick_log(CommonLog.MESSAGE_VOICE_API_FORBID).flush()
        if response.status_code == 200 and result.get('showapi_res_body.flag'):
            CommonLog.add_quick_log(CommonLog.MESSAGE_VOICE_API_SEND_SUCCESS.format(response_message)).flush()
            return True
        else:
            return CommonLog.add_quick_log(CommonLog.MESSAGE_VOICE_API_SEND_FAIL.format(response_message)).flush()

    def send_voice_code_of_dingxin(self, phone, name='', info={}):
        """
        发送语音验证码 ( 鼎信 )
        购买地址 https://market.aliyun.com/products/56928004/cmapi026600.html?spm=5176.2020520132.101.2.51547218rkAXxy
        :return:
        """
        appcode = Config().NOTIFICATION_API_APP_CODE
        if not appcode:
            CommonLog.add_quick_log(CommonLog.MESSAGE_EMPTY_APP_CODE).flush()
            return False
        data = {
            'tpl_id': 'TP1901174',
            'phone': phone,
            'param': 'name:{name},job_name:{left_station}到{arrive_station}{set_type},orderno:{orderno}'.format(
                name=name, left_station=info.get('left_station'), arrive_station=info.get('arrive_station'),
                set_type=info.get('set_type'), orderno=info.get('orderno'))
        }
        response = self.session.request(url=API_NOTIFICATION_BY_VOICE_CODE_DINGXIN, method='POST', data=data,
                                        headers={'Authorization': 'APPCODE {}'.format(appcode)})
        result = response.json()
        response_message = result.get('return_code')
        if response.status_code in [400, 401, 403]:
            return CommonLog.add_quick_log(CommonLog.MESSAGE_VOICE_API_FORBID).flush()
        if response.status_code == 200 and result.get('return_code') == '00000':
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
        message['From'] = Config().EMAIL_SENDER
        message['To'] = to
        message.set_content(content)
        try:
            server = smtplib.SMTP(Config().EMAIL_SERVER_HOST)
            server.login(Config().EMAIL_SERVER_USER, Config().EMAIL_SERVER_PASSWORD)
            server.ehlo()
            server.starttls()
            server.send_message(message)
            server.quit()
            CommonLog.add_quick_log(CommonLog.MESSAGE_SEND_EMAIL_SUCCESS).flush()
        except Exception as e:
            CommonLog.add_quick_log(CommonLog.MESSAGE_SEND_EMAIL_FAIL.format(e)).flush()

    def send_dingtalk_by_webbook(self, content):
        from dingtalkchatbot.chatbot import DingtalkChatbot
        webhook = Config().DINGTALK_WEBHOOK
        dingtalk = DingtalkChatbot(webhook)
        dingtalk.send_text(msg=content, is_at_all=True)
        pass

    def send_to_telegram_bot(self, content):
        bot_api_url = Config().TELEGRAM_BOT_API_URL
        if not bot_api_url:
            return False
        data = {
            'text': content
        }
        response = self.session.request(url=bot_api_url, method='POST', data=data)
        result = response.json().get('result')
        response_status = result.get('statusCode')
        if response_status == 200:
            CommonLog.add_quick_log(CommonLog.MESSAGE_SEND_TELEGRAM_SUCCESS).flush()
        else:
            response_error_message = result.get('description')
            CommonLog.add_quick_log(CommonLog.MESSAGE_SEND_TELEGRAM_FAIL.format(response_error_message)).flush()

    def send_serverchan(self, skey, title, content):
        from lightpush import lightpush
        lgp = lightpush()
        lgp.set_single_push(key=skey)
        try:
            lgp.single_push(title, content)
            CommonLog.add_quick_log(CommonLog.MESSAGE_SEND_SERVER_CHAN_SUCCESS).flush()
        except Exception as e:
            CommonLog.add_quick_log(CommonLog.MESSAGE_SEND_SERVER_CHAN_FAIL.format(e)).flush()

    def send_pushbear(self, skey, title, content):
        from lightpush import lightpush
        lgp = lightpush()
        lgp.set_group_push(key=skey)
        try:
            lgp.group_push(title, content)
            CommonLog.add_quick_log(CommonLog.MESSAGE_SEND_PUSH_BEAR_SUCCESS).flush()
        except Exception as e:
            CommonLog.add_quick_log(CommonLog.MESSAGE_SEND_PUSH_BEAR_SUCCESS.format(e)).flush()


if __name__ == '__main__':
    name = '张三4'
    content = '你的车票 广州 到 深圳 购买成功，请登录 12306 进行支付'
    # Notification.voice_code('13800138000', name, content)
    # Notification.send_email('user@email.com', name, content)
    # Notification.dingtalk_webhook(content)
    Notification.voice_code('13800138000', name, {
        'left_station': '广州',
        'arrive_station': '深圳',
        'set_type': '硬座',
        'orderno': 'E123542'
    })
