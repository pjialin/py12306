from py12306.helpers.func import *
from py12306.log.common_log import CommonLog


def app_available_check():
    now = time_now()
    if now.hour >= 23 or now.hour < 6:
        CommonLog.add_quick_log(CommonLog.MESSAGE_12306_IS_CLOSED.format(time_now())).flush()
        open_time = datetime.datetime(now.year, now.month, now.day, 6)
        if open_time < now:
            open_time += datetime.timedelta(1)
        sleep((open_time - now).seconds)
    return True
