import smtplib
from abc import ABC, abstractmethod
from email.message import EmailMessage
from typing import List
from urllib.parse import urlencode

from app.app import Logger
from app.models import Order, Ticket
from lib.helper import retry
from lib.request import Session


class NotifactionMessage:

    def __init__(self, title: str = '', message: str = '', extra: dict = None) -> None:
        super().__init__()
        self.title = title
        self.message = message
        self.extra = extra or {}

    def to_str(self):
        return f"{self.title}\n\n{self.message}"


class NotifactionAbstract(ABC):

    def __init__(self, config: dict) -> None:
        super().__init__()
        self.session = Session.share()
        self.config = config

    @abstractmethod
    async def send(self, message: NotifactionMessage) -> bool:
        pass


class NotificationCenter:
    """ 通知类 """

    def __init__(self):
        self.backends: List[NotifactionAbstract] = []

    def add_backend(self, backend: NotifactionAbstract):
        self.backends.append(backend)

    async def order_success_notifation(self, order: Order):
        body = f"请及时登录12306账号[{order.user.name}]，打开 '未完成订单'，在30分钟内完成支付!" \
            # f"\n\n车次信息： {} {}[{}] -> {}[{}]，乘车日期 {}，席位：{}，乘车人：{}"
        # TODO
        message = NotifactionMessage(title='车票购买成功！', message=body)
        message.extra = {
            'name': order.user.real_name,
            'left_station': '广州',
            'arrive_station': '深圳',
            'set_type': '硬座',
            'orderno': 'E123542'
        }
        await self.send_message(message)

    async def ticket_available_notifation(self, ticket: Ticket):
        title = f'余票监控通知 {ticket.route_text}'
        body = f'{ticket.detail_text}'
        await self.send_message(NotifactionMessage(title=title, message=body))

    async def send_message(self, message: NotifactionMessage):
        for backend in self.backends:
            await backend.send(message)


class DingTalkNotifaction(NotifactionAbstract):
    """ 钉钉 """

    @retry
    async def send(self, message: NotifactionMessage) -> bool:
        api_url = f"https://oapi.dingtalk.com/robot/send?access_token={self.config.get('access_token')}"
        data = {'msgtype': 'text', 'text': {'content': message.to_str()}}
        response = await self.session.request('POST', api_url, json=data)
        result = response.json()
        if result.get('errcode') == 0:
            Logger.info('钉钉 推送成功')
            return True
        Logger.info(f"钉钉 推送失败，{result.get('errmsg')}")
        return False


class BarkNotifaction(NotifactionAbstract):
    """ Bark """

    @retry
    async def send(self, message: NotifactionMessage) -> bool:
        api_url = f"{self.config.get('push_url')}/{message.to_str()}"
        response = await self.session.request('GET', api_url)
        result = response.json()
        if result.get('code') == 200:
            Logger.info('Bark 推送成功')
            return True
        Logger.info(f"Bark 推送失败，{result.get('message')}")
        return False


class EmailNotifaction(NotifactionAbstract):
    """ Email """

    @retry
    async def send(self, message: NotifactionMessage) -> bool:
        to = self.config.get('to')
        if not to:
            Logger.warning('未配置邮件接受用户')
            return False
        to = to if isinstance(to, list) else [to]
        email_message = EmailMessage()
        email_message['Subject'] = message.title
        email_message['From'] = self.config.get('sender', '')
        email_message['To'] = to
        email_message.set_content(message.message)
        try:
            server = smtplib.SMTP(self.config.get('host'))
            server.ehlo()
            server.starttls()
            server.login(self.config.get('user', ''), self.config.get('password', ''))
            server.send_message(email_message)
            server.quit()
            Logger.info('邮件发送成功，请检查收件箱')
            return True
        except Exception as e:
            Logger.error(f'邮件发送失败，请手动检查配置，错误原因 {e}')
        return False


class ServerChanNotifaction(NotifactionAbstract):
    """ ServerChan
    http://sc.ftqq.com/3.version
    """

    @retry
    async def send(self, message: NotifactionMessage) -> bool:
        api_url = f"https://sc.ftqq.com/{self.config.get('sckey')}.send"
        data = {'text': message.title, 'desp': message.message}
        response = await self.session.request('POST', api_url, data=data)
        result = response.json()
        if result.get('errno') == 0:
            Logger.info('ServerChan 推送成功')
            return True
        Logger.info(f"ServerChan 推送失败，{result.get('error_message', result.get('errmsg'))}")
        return False


class PushBearNotifaction(NotifactionAbstract):
    """ PushBear # 已失效
    http://pushbear.ftqq.com/admin/#/
   """

    @retry
    async def send(self, message: NotifactionMessage) -> bool:
        api_url = f"https://pushbear.ftqq.com/sub?sendkey={self.config.get('sendkey')}&"
        querys = {'text': message.title, 'desp': message.message}
        response = await self.session.request('GET', api_url + urlencode(querys))
        result = response.json()
        if result.get('code') == 0:
            Logger.info('PushBear 推送成功')
            return True
        Logger.info(f"PushBear 推送失败，{result.get('errmsg')}")
        return False


class DingXinVoiceNotifaction(NotifactionAbstract):
    """ 发送语音验证码 ( 鼎信 )
    购买地址 https://market.aliyun.com/products/56928004/cmapi026600.html?spm=5176.2020520132.101.2.51547218rkAXxy
    """

    @retry
    async def send(self, message: NotifactionMessage) -> bool:
        phone = self.config.get('phone')
        if not phone:
            Logger.warning('未配置语音通知手机号')
            return False
        api_url = f"http://yuyin2.market.alicloudapi.com/dx/voice_notice"
        headers = {'Authorization': f"APPCODE {self.config.get('appcode')}"}
        data = {
            'tpl_id': 'TP1901174',
            'phone': phone,
            'param': f"name:{message.extra.get('name', '')},job_name:{message.extra.get('left_station', '')}"
                     f"到{message.extra.get('arrive_station', '')}{message.extra.get('set_name', '')},"
                     f"orderno:{message.extra.get('orderno', '')}"}
        response = await self.session.request('POST', api_url, headers=headers, data=data)
        result = response.json()
        if result.get('return_code') in [400, 401, 403]:
            Logger.error('语音消息发送失败，请检查 appcode 是否填写正确或 套餐余额是否充足')
        elif result.get('return_code') == '00000':
            Logger.info(f"语音消息发送成功!")
            return True
        Logger.info(f"语音消息发送失败，{result.get('return_code')}")
        return False
