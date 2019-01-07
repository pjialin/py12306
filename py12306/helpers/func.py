import datetime
import random
import threading
from time import sleep

from py12306 import config
import functools


def singleton(cls):
    """
    将一个类作为单例
    来自 https://wiki.python.org/moin/PythonDecoratorLibrary#Singleton
    """

    cls.__new_original__ = cls.__new__

    @functools.wraps(cls.__new__)
    def singleton_new(cls, *args, **kw):
        it = cls.__dict__.get('__it__')
        if it is not None:
            return it

        cls.__it__ = it = cls.__new_original__(cls, *args, **kw)
        it.__init_original__(*args, **kw)
        return it

    cls.__new__ = singleton_new
    cls.__init_original__ = cls.__init__
    cls.__init__ = object.__init__

    return cls


# 座位
def get_seat_number_by_name(name):
    return config.SEAT_TYPES[name]


def get_seat_name_by_number(number):
    return [k for k, v in config.SEAT_TYPES.items() if v == number].pop()


# 初始化间隔
def init_interval_by_number(number):
    if isinstance(number, dict):
        min = float(number.get('min'))
        max = float(number.get('max'))
    else:
        min = number / 2
        max = number
    return {
        'min': min,
        'max': max
    }


def get_interval_num(interval, decimal=2):
    return round(random.uniform(interval.get('min'), interval.get('max')), decimal)


def stay_second(second):
    sleep(second)


def is_main_thread():
    return threading.current_thread() == threading.main_thread()


def current_thread_id():
    return threading.current_thread().ident


def time_now():
    return datetime.datetime.now()


def create_thread_and_run(jobs, callback_name, wait=True, daemon=True):
    threads = []
    if not isinstance(jobs, list):
        jobs = [jobs]
    for job in jobs:
        thread = threading.Thread(target=getattr(job, callback_name))
        thread.setDaemon(daemon)
        thread.start()
        threads.append(thread)
    if wait:
        for thread in threads: thread.join()


def dict_find_key_by_value(data, value, default=None):
    result = [k for k, v in data.items() if v == value]
    return result.pop() if len(result) else default


def array_dict_find_by_key_value(data, key, value, default=None):
    result = [v for k, v in enumerate(data) if key in v and v[key] == value]
    return result.pop() if len(result) else default

# def test:
