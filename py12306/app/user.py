import asyncio
import datetime
import json
import math
import random
from base64 import b64decode
from typing import List

from app.app import Config, Logger, Event, App
from app.models import User, QueryJob
from lib.exceptions import RetryException, PassengerNotFoundException
from lib.helper import ShareInstance, UserTypeHelper, TaskManager, retry
from lib.request import TrainSession, Session


class CaptchaTool(ShareInstance):
    """ 登录验证码类 """

    def __init__(self, session=None):
        self.session = session or TrainSession.share()

    @retry()
    async def auth_and_get_answer(self):
        """ 验证验证码，获取答案 """
        captcha_image64 = await self.get_base64_code()
        identify_res = await self.identify_captcha(captcha_image64)
        if identify_res:
            ret = await self.verify_captcha_answer(identify_res)
            if ret:
                return identify_res
        # TODO retry
        return False

    @retry()
    async def get_base64_code(self) -> str:
        Logger.debug('正在下载验证码...')
        response = await self.session.passport_captcha_image64()
        result = response.json()
        if result.get('image'):
            Logger.debug('验证码下载成功')
            return result.get('image')

        raise RetryException()

    @retry()
    async def identify_captcha(self, captcha_image64: str):
        Logger.debug('正在识别验证码...')
        response = await Session.share().identify_captcha(captcha_image64)
        result = response.json()
        if result.get('msg') == 'success':
            pos = result.get('result')
            ret = self.get_image_position_by_offset(pos)
            Logger.debug(f'验证码识别成功，{ret}')
            return ','.join(map(str, ret))

        Logger.error(f'验证码识别失败，{response.reason}')
        return False

    @retry()
    async def verify_captcha_answer(self, answer: str) -> bool:
        """ 校验验证码 """
        Logger.debug('正在校验验证码...')
        response = await self.session.passport_captcha_check(answer)
        result = response.json()
        if result.get('result_code') == '4':
            Logger.info('验证码验证成功')
            return True
        else:
            # {'result_message': '验证码校验失败', 'result_code': '5'}
            Logger.warning('验证码验证失败 错误原因: %s' % result.get('result_message'))
            # TODO clean session
        return False

    @staticmethod
    def get_image_position_by_offset(offsets) -> list:
        """ 坐标转换到像素 """
        positions = []
        width = 75
        height = 75
        for offset in offsets:
            random_x = random.randint(-5, 5)
            random_y = random.randint(-5, 5)
            offset = int(offset)
            x = width * ((offset - 1) % 4 + 1) - width / 2 + random_x
            y = height * math.ceil(offset / 4) - height / 2 + random_y
            positions.append(int(x))
            positions.append(int(y))
        return positions


class TrainUserManager(TaskManager):

    def __init__(self) -> None:
        super().__init__()

    async def run(self):
        self.fuatures.append(asyncio.ensure_future(self.subscribe_loop()))
        while True:
            await self.make_tasks()
            self.clean_fuatures()
            await asyncio.sleep(self.interval)

    @property
    async def task_total(self) -> int:
        return await User.filter(enable=True).count()

    @property
    async def capacity_num(self) -> int:
        if not App.check_12306_service_time():  # debug 拦截，非服务时间登录不可用
            Logger.warning('12306 休息时间，已停用登录')
            return 0
        return await super().capacity_num

    async def subscribe_loop(self):
        while True:
            event = await Event.subscribe()
            if event.name == Event.EVENT_VERIFY_QUERY_JOB:
                await self.verify_query_job(event.data)

    async def make_tasks(self):
        if await self.is_overflow:  # 丢弃多余任务
            self.tasks.popitem()
        for user in await User.all():
            if self.get_task(user.id):
                if not user.enable:
                    self.stop_and_drop(user.id)
                    Logger.debug(f'任务 {user.name_text} 不可用，已停止该任务')
                continue
            if await self.is_full:
                continue
            if Config.redis_able and user.is_alive:
                Logger.debug(f'任务 {user.name_text} 正在运行中已跳过')
                continue
            await self.handle_task(user)

    async def handle_task(self, user: User):
        """ 添加任务 """
        train_user = TrainUser(user)
        Logger.info(f'# 用户 {user.name} 已添加到任务中 #')
        self.add_task(train_user.run(), user.id, train_user)

    async def verify_query_job(self, data: dict):
        """ 验证查询任务信息
        ) 乘客信息验证
        """
        if not isinstance(data, dict) or not data.get('id'):
            return
        user_id = data.get('user_id', 0)
        task: TrainUser = self.get_task(user_id)
        if not task or not task.is_ready:
            return
        query_job = await QueryJob.filter(id=data['id']).first()
        if not query_job:
            return
        ret = task.verify_members(query_job)
        if ret:
            query_job.status = query_job.Status.Normal
        else:
            query_job.status = query_job.Status.Error
            query_job.last_error = '乘客验证失败'
        await query_job.save()
        return


class TrainUser(ShareInstance):
    def __init__(self, user: User) -> None:
        super().__init__()
        self.session = TrainSession()
        self.user: User = user
        self._last_process_at = user.last_process_at
        self._is_ready = False
        self._is_stop = False
        self.is_ordering = False

    async def run(self):
        await self.login_user()
        while not self.is_stoped:
            await self.user.refresh_from_db()
            # 检测同时运行可能导致任务重复
            if self.user.last_process_at != self._last_process_at:
                break
            self._last_process_at = await self.user.update_last_process_at()
            await self._heartbeat_check()
            await asyncio.sleep(Config.USER_HEARTBEAT_INTERVAL)
            if Config.IS_IN_TEST:
                break

    @retry
    async def login_user(self):
        """
        用户登录
        ) 检查用户是否可以恢复
        ) 获取浏览器 ID
        ) 获取验证码识别结果
        ) 请求登录
        ) 获取用户详细信息
        :param user:
        :return:
        """
        if await self._try_restore_user():
            return True
        data = {
            'username': self.user.name,
            'password': self.user.password,
            'appid': 'otn'
        }
        answer = await CaptchaTool(self.session).auth_and_get_answer()
        data['answer'] = answer
        await self.update_device_id()
        response = await self.session.passport_web_login(data)
        result = response.json()
        if result.get('result_code') == 0:  # 登录成功
            return await self.handle_login_next_step()
        elif result.get('result_code') == 2:  # 账号之内错误
            Logger.error(f"登录失败，错误原因: {result.get('result_message')}")
        else:
            Logger.error(f"登录失败，{result.get('result_message', '请求被限制')}")
        raise RetryException(wait_s=5)

    async def handle_login_next_step(self):
        """
        login 获得 cookie uamtk
        auth/uamtk      不请求，会返回 uamtk票据内容为空
        /otn/uamauthclient 能拿到用户名
        """
        uamtk = await self.get_auth_uamtk()
        user_name = await self.get_auth_username(uamtk)
        await self.login_succeeded()
        self._welcome_user()
        return True

    async def update_device_id(self):
        """ 获取加密后的浏览器特征 ID """
        response = await Session.share().browser_device_id_url()
        if response.status == 200:
            result = response.json()
            response = await self.session.browser_device_id(b64decode(result['id']).decode())
            text = response.text()
            if text.find('callbackFunction') >= 0:
                result = text[18:-2]
                result = json.loads(result)
                self.session.session.cookie_jar.update_cookies({
                    'RAIL_EXPIRATION': result.get('exp'),
                    'RAIL_DEVICEID': result.get('dfp'),
                })
        # TODO 错误处理
        return False

    @retry
    async def get_auth_uamtk(self) -> str:
        """ 获取登录 uamtk """
        response = await self.session.passport_web_auth_uamtk()
        result = response.json()
        if result.get('newapptk'):
            return result.get('newapptk')
        raise RetryException('获取 uamtk 失败')

    async def get_auth_username(self, uamtk: str):
        """ 获取登录用户名 """
        response = await self.session.otn_uamauthclient(uamtk)
        result = response.json()
        if result.get('username'):
            return result.get('username')
        raise RetryException('获取 username 失败')

    async def login_succeeded(self):
        """ 登录成功
        ) 更新用户信息
        """
        await self.update_user_info()
        self._save_user_cookies()
        await self.user.save()
        self._is_ready = True

    def _welcome_user(self):
        Logger.info(f'# 欢迎回来，{self.user.real_name} #')

    def _save_user_cookies(self):
        self.user.last_cookies = self.session.cookie_dumps()

    async def update_user_info(self):
        ret: dict = await self.get_user_info()
        self.user.real_name = ret.get('name', '')
        self.user.user_id = ret.get('user_name', '')
        # 更新最后心跳
        self.user.last_heartbeat = datetime.datetime.now()
        # 乘客列表
        self.user.passengers = await self.get_user_passengers()

    @retry
    async def get_user_info(self) -> dict:
        """ 获取用户详情 """
        response = await self.session.otn_modify_user_init_query_user_info()
        result = response.json()
        user_info = result.get('data.userDTO.loginUserDTO')
        if not user_info:
            raise RetryException('获取用户详情失败，请检测用户是否登录')
        return user_info

    @retry
    async def get_user_passengers(self):
        """ 获取乘客列表 """
        response = await self.session.otn_confirm_passenger_get_passenger()
        result = response.json()
        if result.get('data.normal_passengers'):
            return result.get('data.normal_passengers')
        Logger.error(f"获取用户乘客列表失败，{result.get('messages', response.reason)}")
        raise RetryException

    async def _heartbeat_check(self):
        """ 心跳检测 """
        if (datetime.datetime.now() - await self.get_last_heartbeat()).seconds > Config.USER_HEARTBEAT_INTERVAL:
            return True
        if not await self.is_still_logged():
            self._is_ready = False
            self.user.last_cookies = None
            await self.user.save()
            return await self.login_user()

        await self.login_succeeded()
        Logger.info(f'用户 {self.user.real_name} 心跳正常，下次检测 {Config.USER_HEARTBEAT_INTERVAL} 秒后')

    async def _try_restore_user(self) -> bool:
        """ 尝试通过 Cookie 恢复用户 """
        if not self.user.last_cookies:
            return False
        self.session.cookie_loads(self.user.last_cookies)
        if not await self.is_still_logged():
            # 清空 Cookie
            self.session.cookie_clean()
            Logger.info('用户恢复失败，用户状态已过期，正在重新登录...')
            return False

        await self.login_succeeded()
        Logger.info(f'# 用户恢复成功，欢迎回来，{self.user.real_name} #')
        return True

    async def get_last_heartbeat(self) -> datetime.datetime:
        return self.user.last_heartbeat

    @retry
    async def is_still_logged(self) -> bool:
        """ 验证当前登录状态 """
        response = await self.session.otn_login_conf()
        result = response.json()
        if response.status is not 200:
            raise RetryException
        if result.get('data.is_login') == 'Y':
            return True
        return False

    def format_passengers(self, members: list) -> List[dict]:
        """ 获取格式化后的乘客列表
        [{
            name: '贾宝玉',
            type: 1,
            id_card: 0000000000000000000,
            type_text: '成人',
            enc_str: 'xxxxxxxx'
        }]
        """
        ret = []
        _members_tmp = []
        for member in members:
            is_member_id = isinstance(member, int)

            def find_passenger():
                for item in self.user.passengers:
                    if not is_member_id and member[0] == '*':
                        item['passenger_type'] = UserTypeHelper.ADULT
                    if is_member_id and int(item.get('index_id', -1)) == member or \
                            item.get('passenger_name') == member:
                        if member in _members_tmp:
                            item['passenger_type'] = UserTypeHelper.CHILD
                        return item

            passenger = find_passenger()
            if not passenger:
                raise PassengerNotFoundException(member)

            _members_tmp.append(member)
            ret.append({
                'name': passenger.get('passenger_name'),
                'id_card': passenger.get('passenger_id_no'),
                'id_card_type': passenger.get('passenger_id_type_code'),
                'mobile': passenger.get('mobile_no'),
                'type': passenger.get('passenger_type'),
                'type_text': UserTypeHelper.dicts.get(int(passenger.get('passenger_type'))),
                'enc_str': passenger.get('allEncStr')
            })

        return ret

    def verify_members(self, query: QueryJob):
        try:
            passengers = self.format_passengers(query.members)
            if passengers:
                result = [passenger.get('name') + '(' + passenger.get('type_text') + ')' for passenger in passengers]
                Logger.info(f"# 乘客验证成功，{query.route_text} {', '.join(result)} #")
                query.passengers = passengers
                return True
        except PassengerNotFoundException as e:
            Logger.warning(f"# 乘客验证失败，账号 {self.user.name} 中未找到该乘客：{e} #")
        return False

    @property
    def is_stoped(self) -> bool:
        return self._is_stop

    @property
    def is_ready(self) -> bool:
        return self._is_ready

    async def stop(self):
        if self.is_stoped:
            return
        self._is_ready = False
        self._is_stop = True
        self._save_user_cookies()
        await self.user.save()
        Logger.info(f'# 用户 {self.user.real_name} 已退出 #')
