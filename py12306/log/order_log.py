from py12306.log.base import BaseLog
from py12306.helpers.func import *


@singleton
class OrderLog(BaseLog):
    # 这里如果不声明，会出现重复打印，目前不知道什么原因
    logs = []
    thread_logs = {}
    quick_log = []

    MESSAGE_REQUEST_INIT_DC_PAGE_FAIL = '请求初始化订单页面失败'

    MESSAGE_SUBMIT_ORDER_REQUEST_FAIL = '提交订单失败，错误原因 {} \n'
    MESSAGE_SUBMIT_ORDER_REQUEST_SUCCESS = '提交订单成功'
    MESSAGE_CHECK_ORDER_INFO_FAIL = '检查订单失败，错误原因 {} \n'
    MESSAGE_CHECK_ORDER_INFO_SUCCESS = '检查订单成功'

    MESSAGE_GET_QUEUE_INFO_SUCCESS = '获取排队信息成功，目前排队人数 {}, 余票还剩余 {} 张'
    MESSAGE_GET_QUEUE_COUNT_SUCCESS = '排队成功，你当前排在第 {} 位, 余票还剩余 {} 张'
    MESSAGE_GET_QUEUE_LESS_TICKET = '排队失败，目前排队人数已经超过余票张数'
    MESSAGE_GET_QUEUE_COUNT_FAIL = '排队失败，错误原因 {}'

    MESSAGE_CONFIRM_SINGLE_FOR_QUEUE_SUCCESS = '# 提交订单成功！#'
    MESSAGE_CONFIRM_SINGLE_FOR_QUEUE_ERROR = '出票失败，错误原因 {}'
    MESSAGE_CONFIRM_SINGLE_FOR_QUEUE_FAIL = '提交订单失败，错误原因 {}'

    MESSAGE_QUERY_ORDER_WAIT_TIME_WAITING = '排队等待中，排队人数 {}，预计还需要 {} 秒'
    MESSAGE_QUERY_ORDER_WAIT_TIME_FAIL = '排队失败，错误原因 {}'
    MESSAGE_QUERY_ORDER_WAIT_TIME_INFO = '第 {} 次排队，请耐心等待'

    MESSAGE_ORDER_SUCCESS_NOTIFICATION_TITLE = '车票购买成功！'
    MESSAGE_ORDER_SUCCESS_NOTIFICATION_CONTENT = '请及时登录12306，打开 \'未完成订单\'，在30分钟内完成支付!'

    MESSAGE_ORDER_SUCCESS_NOTIFICATION_OF_VOICE_CODE_START_SEND = '正在发送语音通知, 第 {} 次'
    MESSAGE_ORDER_SUCCESS_NOTIFICATION_OF_VOICE_CODE_CONTENT = '你的车票 {} 到 {} 购买成功，请登录 12306 进行支付'

    MESSAGE_ORDER_SUCCESS_NOTIFICATION_OF_EMAIL_CONTENT = '订单号 {}，请及时登录12306，打开 \'未完成订单\'，在30分钟内完成支付!'

    MESSAGE_JOB_CLOSED = '当前任务已结束'

    @classmethod
    def print_passenger_did_deleted(cls, passengers):
        self = cls()
        result = [passenger.get('name') + '(' + passenger.get('type_text') + ')' for passenger in passengers]
        self.add_quick_log('# 删减后的乘客列表 {} #'.format(', '.join(result)))
        self.flush()
        return self

    @classmethod
    def print_ticket_did_ordered(cls, order_id):
        self = cls()
        self.add_quick_log('# 车票购买成功，订单号 {} #'.format(order_id))
        self.flush()
        return self
