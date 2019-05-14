from py12306.log.base import BaseLog
from py12306.helpers.func import *


@singleton
class RedisLog(BaseLog):
    # 这里如果不声明，会出现重复打印，目前不知道什么原因
    logs = []
    thread_logs = {}
    quick_log = []

    MESSAGE_REDIS_INIT_SUCCESS = 'Redis 初始化成功'
