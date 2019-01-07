from os import path

# 12306 账号
USER_ACCOUNTS = []

# 查询任务
QUERY_JOBS = []

# 查询间隔
QUERY_INTERVAL = 1

# 用户心跳检测间隔
USER_HEARTBEAT_INTERVAL = 120

# 多线程查询
QUERY_JOB_THREAD_ENABLED = 0

# 打码平台账号
AUTO_CODE_ACCOUNT = {
    'user': '',
    'pwd': ''
}

SEAT_TYPES = {
    '特等座': 25,
    '商务座': 32,
    '一等座': 31,
    '二等座': 30,
    '软卧': 23,
    '硬卧': 28,
    '硬座': 29,
    '无座': 26,
}

ORDER_SEAT_TYPES = {
    '特等座': 'P',
    '商务座': 9,
    '一等座': 'M',
    '二等座': 'O',
    '软卧': 4,
    '硬卧': 3,
    '硬座': 1,
    '无座': 1,
}

PROJECT_DIR = path.dirname(path.dirname(path.abspath(__file__))) + '/'

# Query
RUNTIME_DIR = PROJECT_DIR + 'runtime/'
QUERY_DATA_DIR = RUNTIME_DIR + 'query/'
USER_DATA_DIR = RUNTIME_DIR + 'user/'

STATION_FILE = PROJECT_DIR + 'data/stations.txt'
CONFIG_FILE = PROJECT_DIR + 'env.py'

# 语音验证码
NOTIFICATION_BY_VOICE_CODE = 0
NOTIFICATION_VOICE_CODE_PHONE = ''
NOTIFICATION_API_APP_CODE = ''

if path.exists(CONFIG_FILE):
    exec(open(CONFIG_FILE, encoding='utf8').read())


class UserType:
    ADULT = 1
    CHILD = 2
    STUDENT = 3
    SOLDIER = 4

    dicts = {
        '成人': ADULT,
        '儿童': CHILD,
        '学生': STUDENT,
        '残疾军人、伤残人民警察': SOLDIER,
    }
