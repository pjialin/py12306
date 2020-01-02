import asyncio
import datetime
import math
import os
import json
import time

from abc import ABC, abstractmethod
from typing import Coroutine, Any, Union
from functools import wraps
from lib.exceptions import RetryException, MaxRetryException


def retry(num: int = 3):
    """ Retry a func """
    from app.app import Logger

    __retry_num_key = '__retry_num'
    __call = None
    if hasattr(num, '__call__'):
        __call = num
        num = 3

    def decorator(func):

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            retry_num = kwargs.get(__retry_num_key, num)
            try:
                if __retry_num_key in kwargs:
                    del kwargs[__retry_num_key]
                return await func(*args, **kwargs)
            except RetryException as err:
                if retry_num > 0:
                    kwargs[__retry_num_key] = retry_num - 1
                    Logger.warning(
                        f"重试 {func.__name__}{f'，{err.msg}' if err.msg else ''}, 剩余次数 {kwargs[__retry_num_key]}")
                    if err.wait_s:
                        await asyncio.sleep(err.wait_s)
                    return await async_wrapper(*args, **kwargs)
                if err.default:
                    return err.default
                raise MaxRetryException(*err.args) from err

        @wraps(func)
        def wrapper(*args, **kwargs):
            retry_num = kwargs.get(__retry_num_key, num)
            try:
                if __retry_num_key in kwargs:
                    del kwargs[__retry_num_key]
                return func(*args, **kwargs)
            except RetryException as err:
                if retry_num > 0:
                    kwargs[__retry_num_key] = retry_num - 1
                    Logger.warning(
                        f"重试 {func.__name__}{f'，{err.msg}' if err.msg else ''}, 剩余次数 {kwargs[__retry_num_key]}")
                    if err.wait_s:
                        time.sleep(err.wait_s)
                    return wrapper(*args, **kwargs)
                if err.default:
                    return err.default
                raise MaxRetryException(*err.args) from err

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    if __call:
        return decorator(__call)
    return decorator


def number_of_time_period(period: str) -> int:
    """
    Example: 23:00 -> 2300
    :param period:
    :return:
    """
    return int(period.replace(':', ''))


def md5(value):
    import hashlib
    return hashlib.md5(json.dumps(value).encode()).hexdigest()


def run_async(coro: Coroutine):
    """
    Simple async runner
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


def json_encoder(obj: Any):
    """ JSON 序列化, 修复时间 """
    if isinstance(obj, datetime.datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')

    if isinstance(obj, datetime.date):
        return obj.strftime('%Y-%m-%d')

    return super().default(obj)


def json_decoder(obj: Any):
    """ JSON 反序列化，加载时间 """
    ret = obj
    if isinstance(obj, list):
        obj = enumerate(obj)
    elif isinstance(obj, dict):
        obj = obj.items()
    else:
        return obj

    for key, item in obj:
        if isinstance(item, (list, dict)):
            ret[key] = json_decoder(item)
        elif isinstance(item, str):
            try:
                if len(item) is 10:
                    ret[key] = datetime.datetime.strptime(item, '%Y-%m-%d').date()
                else:
                    ret[key] = datetime.datetime.strptime(item, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                ret[key] = item
        else:
            ret[key] = item
    return ret


class JSONDecoder(json.JSONDecoder):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parse_array = self.__parse_array
        self.object_hook = json_decoder
        self.scan_once = json.scanner.py_make_scanner(self)

    def __parse_array(self, *args, **kwargs):
        values, end = json.decoder.JSONArray(*args, **kwargs)
        return self.object_hook(values), end


def json_friendly_loads(obj: Any, **kwargs):
    return json.loads(obj, cls=JSONDecoder, **kwargs)


def json_friendly_dumps(obj: Any, **kwargs):
    return json.dumps(obj, ensure_ascii=False, default=json_encoder, **kwargs)


def str_to_date(_str: str):
    if isinstance(_str, datetime.date):
        return _str
    if len(_str) is 10:
        return datetime.datetime.strptime(_str, '%Y-%m-%d').date()
    else:
        return datetime.datetime.strptime(_str, '%Y-%m-%d %H:%M:%S')


def lmap(*args, **kwargs):
    return list(map(*args, **kwargs))


class ShareInstance:
    __session = None

    @classmethod
    def share(cls):
        if not cls.__session or cls is not cls.__session.__class__:
            cls.__session = cls()
        return cls.__session


class SuperDict(dict):
    def get(self, key, default=None, sep='.'):
        keys = key.split(sep)
        for i, key in enumerate(keys):
            try:
                value = self[key]
                if len(keys[i + 1:]) and isinstance(value, SuperDict):
                    return value.get(sep.join(keys[i + 1:]), default=default, sep=sep)
                return value
            except KeyError:
                return self.dict_to_dict(default)

    def __getitem__(self, k):
        return self.dict_to_dict(super().__getitem__(k))

    @classmethod
    def dict_to_dict(cls, value):
        return SuperDict(value) if isinstance(value, dict) else value


class StationHelper(ShareInstance):

    def __init__(self) -> None:
        super().__init__()
        self._stations = []
        self.version = ''
        from app.app import Config
        if os.path.exists(Config.DATA_DIR + 'stationList.json'):
            with open(Config.DATA_DIR + 'stationList.json', 'r', encoding='utf-8') as f:
                ret = json.load(f)
                self._stations = ret['stationList']
                self.version = ret['version_no']

    @classmethod
    def stations(cls):
        return cls.share()._stations

    @classmethod
    def cn_by_id(cls, _id: str):
        self = cls.share()
        for station in self._stations:
            if station.get('id') == _id:
                return station.get('value')
        return ''

    @classmethod
    def id_by_cn(cls, cn: str):
        for station in cls.share()._stations:
            if station.get('value') == cn:
                return station.get('id')
        return ''


class UserTypeHelper:
    ADULT = 1
    CHILD = 2
    STUDENT = 3
    SOLDIER = 4

    dicts = {
        ADULT: '成人',
        CHILD: '儿童',
        STUDENT: '学生',
        SOLDIER: '残疾军人、伤残人民警察'
    }


class TrainSeat:
    NO_SEAT = 26

    ticket = {'一等座': 'ZY', '二等座': 'ZE', '商务座': 'SWZ', '特等座': 'TZ', '硬座': 'YZ', '软座': 'RZ', '硬卧': 'YW', '二等卧': 'YW',
              '软卧': 'RW', '一等卧': 'RW', '高级软卧': 'GR', '动卧': 'SRRB', '高级动卧': 'YYRW', '无座': 'WZ'}
    ticket_id = {'一等座': 31, '二等座': 30, '商务座': 32, '特等座': 25, '硬座': 29, '软座': 24, '硬卧': 28, '二等卧': 28,
                 '软卧': 23, '一等卧': 23, '高级软卧': 21, '动卧': 33, '高级动卧': -1, '无座': 26}
    order_id = {'棚车': '0', '硬座': '1', '软座': '2', '硬卧': '3', '软卧': '4', '包厢硬卧': '5', '高级软卧': '6', '一等软座': '7',
                '二等软座': '8', '商务座': '9', '高级动卧': 'A', '混编硬座': 'B', '混编硬卧': 'C', '包厢软座': 'D', '特等软座': 'E', '动卧': 'F',
                '二人软包': 'G', '一人软包': 'H', '一等卧': 'I', '二等卧': 'J', '混编软座': 'K', '混编软卧': 'L', '一等座': 'M', '二等座': 'O',
                '特等座': 'P', '观光座': 'Q', '一等包座': 'S', '无座': 'WZ'}


class TaskManager(ABC, ShareInstance):
    __session = None

    def __init__(self) -> None:
        super().__init__()
        self.fuatures = []
        self.tasks = {}
        self.interval = 5

    @abstractmethod
    async def run(self):
        """ """
        pass

    @property
    @abstractmethod
    async def task_total(self) -> int:
        """ 任务总数 """
        pass

    async def wait(self):
        if self.fuatures:
            await asyncio.wait(self.fuatures)

    @property
    async def capacity_num(self) -> int:
        from app.app import Config
        if not Config.node_num:
            return 0
        return math.ceil((await self.task_total) / Config.node_num)

    @property
    def task_num(self) -> int:
        return len(self.tasks)

    def add_task(self, future, _id: Union[str, int], data: Any):
        future = asyncio.ensure_future(future)
        self.fuatures.append(future)
        self.tasks[_id] = data
        return self

    @property
    async def is_full(self) -> bool:
        return self.task_num >= await self.capacity_num

    @property
    async def is_overflow(self) -> bool:
        return self.task_num > await self.capacity_num

    def get_task(self, _key, default=None):
        return self.tasks.get(_key, default)

    def stop_and_drop(self, _key):
        task = self.tasks[_key]
        task.stop()
        del self.tasks[_key]

    def clean_fuatures(self):
        [self.fuatures.remove(fut) for fut in self.fuatures if fut.done()]
