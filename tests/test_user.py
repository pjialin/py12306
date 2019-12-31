from app.models import User
from app.user import TrainUser, CaptchaTool, TrainUserManager
from tests import BaseTest, async_test


class TestCaptchaTool(BaseTest):

    def setUp(self) -> None:
        super().setUp()
        self.captcha_tool = CaptchaTool.share()

    @async_test
    async def test_get_base64_code(self):
        ret = await self.captcha_tool.get_base64_code()
        self.assertIsInstance(ret, str)

    @async_test
    async def test_identify_captcha(self):
        captcha_image64 = await self.captcha_tool.get_base64_code()
        ret = await self.captcha_tool.identify_captcha(captcha_image64)
        self.assertIsInstance(ret, str)

    @async_test
    async def test_verify_captcha_answer(self):
        captcha_image64 = await self.captcha_tool.get_base64_code()
        ret = await self.captcha_tool.identify_captcha(captcha_image64)
        ret = await self.captcha_tool.verify_captcha_answer(ret)
        self.assertTrue(ret)


class TestUser(BaseTest):

    @async_test
    async def setUp(self) -> None:
        super().setUp()
        self.user = await User.first()
        self.train_user = TrainUser(self.user)

    @async_test
    async def test_login_user(self):
        self.user.last_cookies = {}
        ret = await self.train_user.login_user()
        self.assertTrue(ret)

    @async_test
    async def test_update_device_id(self):
        await self.train_user.update_device_id()
        cookies = self.train_user.session.session.cookie_jar._cookies
        self.assertIsInstance(cookies.get('').get('RAIL_DEVICEID').value, str)
        self.assertIsInstance(cookies.get('').get('RAIL_EXPIRATION').value, str)

    @async_test
    async def test_get_user_info(self):
        await self.train_user.login_user()
        ret = await self.train_user.get_user_info()
        self.assertIn('name', ret)
        self.assertIn('user_name', ret)

    @async_test
    async def test_get_user_passengers(self):
        await self.train_user.login_user()
        ret = await self.train_user.get_user_passengers()
        self.assertGreater(len(ret), 1)
