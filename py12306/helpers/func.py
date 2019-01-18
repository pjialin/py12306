# -*- coding: utf-8 -*-
import datetime
import hashlib
import json
import os
import random
import threading
import functools
import time

from time import sleep
from types import MethodType


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


# 座位 # TODO
# def get_number_by_name(name):
#     return config.SEAT_TYPES[name]


# def get_seat_name_by_number(number): # TODO remove config
# return [k for k, v in config.SEAT_TYPES.items() if v == number].pop()


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


def stay_second(second, call_back=None):
    sleep(second)
    if call_back:
        return call_back()


def sleep_forever():
    """
    当不是主线程时，假象停止
    :return:
    """
    if not is_main_thread():
        while True: sleep(10000000)


def is_main_thread():
    return threading.current_thread() == threading.main_thread()


def current_thread_id():
    return threading.current_thread().ident


def time_now():
    return datetime.datetime.now()


def timestamp_to_time(timestamp):
    time_struct = time.localtime(timestamp)
    return time.strftime('%Y-%m-%d %H:%M:%S', time_struct)


def get_file_modify_time(filePath):
    timestamp = os.path.getmtime(filePath)
    return timestamp_to_time(timestamp)


def get_file_total_line_num(file, encoding='utf-8'):
    with open(file, 'r', encoding=encoding) as f:
        return len(f.readlines())


def touch_file(path):
    with open(path, 'a'): pass


def pick_file_lines(file, lines):
    return [x for i, x in enumerate(file) if i in lines]


def str_to_time(str):
    return datetime.datetime.strptime(str, '%Y-%m-%d %H:%M:%S.%f')


def time_int():
    return int(time.time())


def is_number(val):
    if isinstance(val, int): return val
    if isinstance(val, str): return val.isdigit()
    return False


def create_thread_and_run(jobs, callback_name, wait=True, daemon=True, args=(), kwargs={}):
    threads = []
    if not isinstance(jobs, list): jobs = [jobs]
    for job in jobs:
        thread = threading.Thread(target=getattr(job, callback_name), args=args, kwargs=kwargs)
        thread.setDaemon(daemon)
        thread.start()
        threads.append(thread)
    if wait:
        for thread in threads: thread.join()


def jobs_do(jobs, do):
    if not isinstance(jobs, list): jobs = [jobs]
    for job in jobs:
        getattr(job, do)()


def dict_find_key_by_value(data, value, default=None):
    result = [k for k, v in data.items() if v == value]
    return result.pop() if len(result) else default


def objects_find_object_by_key_value(objects, key, value, default=None):
    result = [obj for obj in objects if getattr(obj, key) == value]
    return result.pop() if len(result) else default


def dict_count_key_num(data: dict, key, like=False):
    count = 0
    for k in data.keys():
        if like:
            if k.find(key) >= 0: count += 1
        elif k == key:
            count += 1
    return count


def array_dict_find_by_key_value(data, key, value, default=None):
    result = [v for k, v in enumerate(data) if key in v and v[key] == value]
    return result.pop() if len(result) else default


def get_true_false_text(value, true='', false=''):
    if value: return true
    return false


def sleep_forever_when_in_test():
    if Const.IS_TEST: sleep_forever()


def expand_class(cls, key, value, keep_old=True):
    if (keep_old):
        setattr(cls, 'old_' + key, getattr(cls, key))
    setattr(cls, key, MethodType(value, cls))
    return cls


def available_value(value):
    if isinstance(value, str) or isinstance(value, bytes):
        return value
    return str(value)


def md5(value):
    return hashlib.md5(json.dumps(value).encode()).hexdigest()


@singleton
class Const:
    IS_TEST = False
    IS_TEST_NOTIFICATION = False
