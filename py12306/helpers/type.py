from py12306.helpers.func import *


@singleton
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


@singleton
class OrderSeatType:
    dicts = {
        '特等座': 'P',
        '商务座': 9,
        '一等座': 'M',
        '二等座': 'O',
        '软卧': 4,
        '硬卧': 3,
        '动卧': 1,
        '软座': 2,
        '硬座': 1,
        '无座': 1,
    }


@singleton
class SeatType:
    NO_SEAT = 26
    dicts = {
        '特等座': 25,
        '商务座': 32,
        '一等座': 31,
        '二等座': 30,
        '软卧': 23,
        '硬卧': 28,
        '动卧': 33,
        '软座': 24,
        '硬座': 29,
        '无座': NO_SEAT,
    }
