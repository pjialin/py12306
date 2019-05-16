import threading


def new_thread_with_jobs(jobs, wait=True, daemon=True, args=(), kwargs={}):
    """
    Run each job with a new thread
    :param jobs:
    :param wait:
    :param daemon:
    :param args:
    :param kwargs:
    :return:
    """
    threads = []
    if not isinstance(jobs, list):
        jobs = [jobs]
    for job in jobs:
        thread = threading.Thread(target=job, args=args, kwargs=kwargs)
        thread.setDaemon(daemon)
        thread.start()
        threads.append(thread)
    if wait:
        for thread in threads:
            thread.join()


def expand_class(cls, key, value, keep_old=True):
    """
    Expand class method
    :param cls:
    :param key:
    :param value:
    :param keep_old:
    :return:
    """
    from types import MethodType

    if keep_old:
        setattr(cls, 'old_' + key, getattr(cls, key))
    setattr(cls, key, MethodType(value, cls))
    return cls


def retry(num: int = 3):
    """
    Retry a func
    :param num:
    :return:
    """
    from py12306.lib.exceptions import RetryException, MaxRetryException
    retry_num_key = '_retry_num'

    def decorator(func):
        def wrapper(*args, **kwargs):
            retry_num = num
            if retry_num_key in kwargs:
                retry_num = kwargs.get(retry_num_key)
                kwargs.pop('_retry_num')
            try:
                res = func(*args, **kwargs)
            except RetryException as err:
                retry_num -= 1
                from py12306.app.app import Logger
                Logger.warning('重试 %s, 剩余次数 %s' % (func.__name__, retry_num))
                if retry_num > 0:
                    kwargs[retry_num_key] = retry_num
                    return wrapper(*args, **kwargs)
                raise MaxRetryException(*err.args) from None

            return res

        return wrapper

    return decorator


def number_of_time_period(period: str) -> int:
    """
    Example: 23:00 -> 2300
    :param period:
    :return:
    """
    return int(period.replace(':', ''))
