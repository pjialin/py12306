import logging
import os
import sys

import aioredis
import toml
from aioredis import Redis
from tortoise import Tortoise

from lib.exceptions import LoadConfigFailException
from lib.hammer import *
from lib.helper import SuperDict


class ConfigInstance:
    APP_NAME = 'py12306'
    DEBUG = False
    IS_IN_TEST = False
    PROJECT_DIR = os.path.abspath(__file__ + '/../../../') + '/'
    DATA_DIR = PROJECT_DIR + 'data/'
    CONFIG_FILE = PROJECT_DIR + 'config.toml'
    CONFIG_TEST_FILE = PROJECT_DIR + 'config_test.toml'
    QUERY_AVAILABLE = False

    # 默认请求超时
    REQUEST_TIME_OUT = 5
    # 用户心跳检测间隔
    USER_HEARTBEAT_INTERVAL = 120
    # USER_HEARTBEAT_INTERVAL = 10

    # Config
    REDIS = {
        'enable': False,
        'host': '127.0.0.1', 'port': 6379, 'db': 0, 'password': None, 'decode_responses': True
    }
    DATABASE = {
        'db_url': f'sqlite://{DATA_DIR}db.sqlite3',
    }
    Notifaction = {}

    _configs = {}

    def load(self):
        """ Load configs from toml file """
        for arg in sys.argv:
            if arg.find('unittest') >= 0:
                self.IS_IN_TEST = True
        file_path = self.CONFIG_FILE
        if self.IS_IN_TEST and os.path.isfile(self.CONFIG_TEST_FILE):
            file_path = self.CONFIG_TEST_FILE
        configs = toml.load(file_path)
        self._configs = SuperDict(configs)
        self.REDIS.update(configs.get('redis', {}))
        db = configs.get('db', {})
        if db and db.get('engine') in ['mysql']:
            db['db_url'] = f"{db.get('engine')}://{db.get('user')}:{db.get('password')}@{db.get('host')}:{db.get('port')}/{db.get('database')}"
        self.DATABASE.update(configs.get('db', {}))
        self.DEBUG = self._configs.get('app.debug', self.DEBUG)
        self.Notifaction: dict = self._configs.get('notifaction', self.Notifaction)
        return self

    @property
    def node_num(self) -> int:
        if not Config.QUERY_AVAILABLE:
            return 0
        # TODO
        return 1

    @property
    def redis_able(self) -> bool:
        return self.REDIS.get('enable', False)

    @property
    def proxy_able(self) -> bool:
        return self.get('proxy.enable', False)

    def get(self, key, default=None):
        return self._configs.get(key, default)


class App:
    __instance = False

    def __new__(cls) -> Any:
        if cls.__instance:
            return cls.__instance
        return super().__new__(cls)

    def __init__(self) -> None:
        super().__init__()
        self.__class__.__instance = self
        self.__features = []

    def start_run_loop(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.__run_loop())

    async def __run_loop(self):
        self.print_welcome()
        await self.init_db()
        await self.__load_data()
        await self.__run_query_loop()
        ret = await asyncio.wait(self.__features, return_when=asyncio.FIRST_COMPLETED)

    async def __run_query_loop(self):
        """ 12306 查询相关
        ) 服务时间检测
        """
        from app.user import TrainUserManager
        from app.query import QueryTicketManager
        from app.order import OrderTicketManager
        self.__features.append(self.__service_check_loop())
        self.__features.append(TrainUserManager.share().run())
        self.__features.append(QueryTicketManager.share().run())
        self.__features.append(OrderTicketManager.share().run())

    async def __service_check_loop(self):
        last_check = None
        while True:
            if not Config.DEBUG and not self.check_12306_service_time():
                if not last_check or (datetime.datetime.now() - last_check).seconds > 3600:
                    Logger.info(f'程序运行中，当前时间: {datetime.datetime.now()}   |   12306 休息时间，程序将在明天早上 6 点自动运行')
                    last_check = datetime.datetime.now()
                Config.QUERY_AVAILABLE = False
            else:
                Config.QUERY_AVAILABLE = True
            await asyncio.sleep(1)

    async def init_db(self):
        await Tortoise.init(
            db_url=Config.DATABASE['db_url'],
            modules={'models': ['app.models']})
        # Generate the schema
        await Tortoise.generate_schemas()

    def check_12306_service_time(self):
        """ 服务时间检测 """
        now = datetime.datetime.now()
        if (now.hour >= 23 and now.minute >= 30) or now.hour < 6:
            return False
        return True

    def print_welcome(self):
        Logger.info('######## py12306 购票助手，本程序为开源工具，请勿用于商业用途 ########')
        if Config.DEBUG:
            Logger.info('Debug 模式已启用')

    async def __load_data(self):
        """ 加载配置数据
        ) 加载用户
        ) 加载查询
        """
        from app.models import User
        from app.models import QueryJob
        try:
            users = Config.get('user', [])
            for _user in users:
                await User.load_from_config(_user)
            querys = Config.get('query', [])
            for _query in querys:
                await QueryJob.load_from_config(_query)
        except LoadConfigFailException as e:
            Logger.error(f'配置验证失败，{e.msg}')
            await self.exit()

    async def exit(self, msg: str = ''):
        await Tortoise.close_connections()
        Logger.info('# 程序已退出 #')
        sys.exit(msg)


# set up logger
def __set_up_logger() -> logging.Logger:
    logger = logging.getLogger(Config.APP_NAME)
    logger.setLevel('DEBUG' if Config.DEBUG else 'INFO')
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def __load_event():
    engine = AsyncioEventEngine
    if Config.redis_able:
        engine = RedisEventEngine
    return EventHammer(engine())


def __load_cache():
    engine = AsyncioCacheEngine
    if Config.redis_able:
        engine = RedisCacheEngine
    return CacheHammer(engine())


def __load_redis() -> Redis:
    if Config.redis_able:
        addrss = f"redis://{Config.REDIS['host']}:{Config.REDIS['port']}"
        return asyncio.get_event_loop().run_until_complete(
            aioredis.create_redis_pool(addrss, db=Config.REDIS['db'], password=Config.REDIS['password']))
    return None


def __load_notifaction():
    from app import notification as nt
    center = nt.NotificationCenter()
    conf = Config.Notifaction
    if conf.get('ding_talk.enable'):
        center.add_backend(nt.DingTalkNotifaction(conf['ding_talk']))
    if conf.get('bark.enable'):
        center.add_backend(nt.BarkNotifaction(conf['bark']))
    if conf.get('email.enable'):
        center.add_backend(nt.EmailNotifaction(conf['email']))
    if conf.get('server_chan.enable'):
        center.add_backend(nt.ServerChanNotifaction(conf['server_chan']))
    if conf.get('ding_xing_voice.enable'):
        center.add_backend(nt.DingXinVoiceNotifaction(conf['ding_xing_voice']))
    return center


# load config
Config = ConfigInstance().load()
Redis = __load_redis()
Logger = __set_up_logger()
Event = __load_event()
Cache = __load_cache()
Notification = __load_notifaction()
App = App()
