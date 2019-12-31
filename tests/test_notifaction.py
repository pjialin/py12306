from app.app import Config
from app.notification import *
from tests import BaseTest, async_test


class NotifactionTests(BaseTest):

    def setUp(self) -> None:
        super().setUp()
        self.message = NotifactionMessage('title', 'body')
        self.ding_talk_config = Config.Notifaction.get('ding_talk', {})
        self.bark_config = Config.Notifaction.get('bark', {})
        self.email_config = Config.Notifaction.get('email', {})
        self.server_chan_config = Config.Notifaction.get('server_chan', {})
        self.push_bear_config = Config.Notifaction.get('push_bear', {})
        self.ding_xing_voice_config = Config.Notifaction.get('ding_xing_voice', {})

    @async_test
    async def test_ding_talk(self):
        if not self.ding_talk_config:
            return
        ret = await DingTalkNotifaction(self.ding_talk_config).send(self.message)
        self.assertTrue(ret)

    @async_test
    async def test_bark(self):
        if not self.bark_config:
            return
        ret = await BarkNotifaction(self.bark_config).send(self.message)
        self.assertTrue(ret)

    @async_test
    async def test_email(self):
        if not self.email_config:
            return
        ret = await EmailNotifaction(self.email_config).send(self.message)
        self.assertTrue(ret)

    @async_test
    async def test_server_chan(self):
        if not self.server_chan_config:
            return
        ret = await ServerChanNotifaction(self.server_chan_config).send(self.message)
        self.assertTrue(ret)

    @async_test
    async def test_push_bear(self):
        if not self.push_bear_config:
            return
        ret = await PushBearNotifaction(self.push_bear_config).send(self.message)
        self.assertTrue(ret)

    @async_test
    async def test_ding_xing_voice(self):
        if not self.ding_xing_voice_config:
            return
        self.message.extra = {
            'name': '贾政',
            'left_station': '广州',
            'arrive_station': '深圳',
            'set_name': '硬座',
            'orderno': 'E123542'
        }
        ret = await DingXinVoiceNotifaction(self.ding_xing_voice_config).send(self.message)
        self.assertTrue(ret)
