import logging
import os


class Config:
    class AppEnvType:
        DEV = 'dev'
        PRODUCTION = 'production'

    APP_NAME = 'py12306'
    APP_ENV = AppEnvType.PRODUCTION
    LOADED = False
    TEST_MODE = False

    PROJECT_DIR = os.path.abspath(__file__ + '/../../../') + '/'
    CONFIG_FILE = PROJECT_DIR + 'config.toml'

    # Config
    REDIS = {
        'host': '127.0.0.1',
        'port': 6379,
        'db': 0,
        'password': None,
        'decode_responses': True
    }

    # Redis keys
    REDIS_PREFIX_KEY_TASKS = 'tasks:'

    # REDIS_KEY_USER_TASKS = 'user_jobs'

    @classmethod
    def load(cls):
        """
        Load configs from toml file
        :return:
        """
        import toml
        configs = toml.load(cls.CONFIG_FILE)

        redis = configs.get('redis')
        if redis:
            cls.REDIS.update(redis)

        app = configs.get('app')
        if app:
            cls.APP_ENV = app.get('env', cls.APP_ENV)


if not Config.LOADED:
    Config.load()

# Logger
Logger = logging.getLogger(Config.APP_NAME)
Logger.setLevel('DEBUG' if Config.APP_ENV == Config.AppEnvType.DEV else 'ERROR')
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
handler.setFormatter(formatter)
Logger.addHandler(handler)
