# from py12306.config import get_value_by_key
from py12306.config import get_value_by_key


class BaseConfig:
    AA = 'USER_ACCOUNTS'


class Config(BaseConfig):

    @classmethod
    def get(cls, key, default=None):
        self = cls()
        return get_value_by_key(key);
