import urllib
import random

from py12306.config import UserType
from py12306.helpers.api import *
from py12306.helpers.app import *
from py12306.helpers.func import *
from py12306.helpers.notification import Notification
from py12306.log.order_log import OrderLog
from py12306.log.user_log import UserLog


# from py12306.query.job import Job
# from py12306.user.job import UserJob


class Order:
    """
    处理下单
    """
    session = None
    query_ins = None
    user_ins = None

    passenger_ticket_str = ''
    old_passenger_str = ''

    is_need_auth_code = False

    max_queue_wait = 120
    current_queue_wait = 0
    retry_time = 3
    wait_queue_interval = 3

    order_id = 0

    notification_sustain_time = 60 * 30  # 通知持续时间 30 分钟
    notification_interval = 5 * 60  # 通知间隔

    def __init__(self, query, user):
        self.session = user.session
        # assert isinstance(query, Job)  # 循环引用
        # assert isinstance(user, UserJob)
        self.query_ins = query
        self.user_ins = user

        self.make_passenger_ticket_str()

    def order(self):
        """
        开始下单
        下单模式  暂时不清楚，使用正常步骤下单
        :return:
        """
        self.normal_order()
        pass

    def normal_order(self):
        if not self.submit_order_request(): return
        if not self.user_ins.request_init_dc_page(): return
        if not self.check_order_info(): return
        if not self.get_queue_count(): return
        if not self.confirm_single_for_queue(): return
        order_id = self.query_order_wait_time()
        if order_id:  # 发送通知
            self.order_id = order_id
            self.order_did_success()

    def order_did_success(self):
        OrderLog.print_ticket_did_ordered(self.order_id)
        OrderLog.notification(OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_TITLE,
                              OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_CONTENT)
        self.send_notification()

    def send_notification(self):
        num = 0  # 通知次数
        sustain_time = self.notification_sustain_time
        while sustain_time:  # TODO 后面直接查询有没有待支付的订单就可以
            num += 1
            if config.NOTIFICATION_BY_VOICE_CODE:  # 语音通知
                OrderLog.add_quick_log(OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_OF_VOICE_CODE_START_SEND.format(num))
                Notification.voice_code(config.NOTIFICATION_VOICE_CODE_PHONE, self.user_ins.get_name(),
                                        OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_OF_VOICE_CODE_CONTENT.format(
                                            self.query_ins.left_station, self.query_ins.arrive_station))
            sustain_time -= self.notification_interval
            sleep(self.notification_interval)

        OrderLog.add_quick_log(OrderLog.MESSAGE_JOB_CLOSED)
        # 结束运行
        while True: sleep(self.retry_time)

    def submit_order_request(self):
        data = {
            'secretStr': urllib.parse.unquote(self.query_ins.get_info_of_secret_str()),  # 解密
            'train_date': self.query_ins.left_date,  # 出发时间
            'back_train_date': self.query_ins.left_date,  # 返程时间
            'tour_flag': 'dc',  # 旅途类型
            'purpose_codes': 'ADULT',  # 成人 | 学生
            'query_from_station_name': self.query_ins.left_station,
            'query_to_station_name': self.query_ins.arrive_station,
        }
        response = self.session.post(API_SUBMIT_ORDER_REQUEST, data)
        result = response.json()
        if result.get('data') == 'N':
            OrderLog.add_quick_log(OrderLog.MESSAGE_SUBMIT_ORDER_REQUEST_SUCCESS).flush()
            return True
        else:
            if (str(result.get('messages', '')).find('未处理') >= 0):  # 未处理订单
                stay_second(self.retry_time)
            OrderLog.add_quick_log(
                OrderLog.MESSAGE_SUBMIT_ORDER_REQUEST_FAIL.format(result.get('messages', '-'))).flush()
        return False

    def check_order_info(self):
        """
        cancel_flag=2
        bed_level_order_num=000000000000000000000000000000
        passengerTicketStr=
        tour_flag=dc
        randCode=
        whatsSelect=1
        _json_att=
        REPEAT_SUBMIT_TOKEN=458bf1b0a69431f34f9d2e9d3a11cfe9
        :return:
        """
        data = {  #
            'cancel_flag': 2,
            'bed_level_order_num': '000000000000000000000000000000',
            'passengerTicketStr': self.passenger_ticket_str,
            'oldPassengerStr': self.old_passenger_str,
            'tour_flag': 'dc',
            'randCode': '',
            'whatsSelect': '1',
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': self.user_ins.global_repeat_submit_token
        }
        response = self.session.post(API_CHECK_ORDER_INFO, data)
        result = response.json()
        if result.get('data.submitStatus'):  # 成功
            OrderLog.add_quick_log(OrderLog.MESSAGE_CHECK_ORDER_INFO_SUCCESS).flush()
            if result.get('data.ifShowPassCode') != 'N':
                self.is_need_auth_code = True
            return True
        else:
            result_data = result.get('data', {})
            OrderLog.add_quick_log(OrderLog.MESSAGE_CHECK_ORDER_INFO_FAIL.format(
                result_data.get('errMsg', result.get('messages', '-'))
            )).flush()
        return False

    def get_queue_count(self):
        """
        获取队列人数
        train_date	Mon Jan 01 2019 00:00:00 GMT+0800 (China Standard Time)
        train_no	630000Z12208
        stationTrainCode	Z122
        seatType	4
        fromStationTelecode	GZQ
        toStationTelecode	RXW
        leftTicket	CmDJZYrwUoJ1jFNonIgPzPFdMBvSSE8xfdUwvb2lq8CCWn%2Bzk1vM3roJaHk%3D
        purpose_codes	00
        train_location	QY
        _json_att
        REPEAT_SUBMIT_TOKEN	0977caf26f25d1da43e3213eb35ff87c
        :return:
        """
        data = {  #
            'train_date': '{} 00:00:00 GMT+0800 (China Standard Time)'.format(
                datetime.datetime.today().strftime("%a %h %d %Y")),
            'train_no': self.user_ins.ticket_info_for_passenger_form['queryLeftTicketRequestDTO']['train_no'],
            'stationTrainCode': self.user_ins.ticket_info_for_passenger_form['queryLeftTicketRequestDTO'][
                'station_train_code'],
            'seatType': self.query_ins.current_order_seat,
            'fromStationTelecode': self.user_ins.ticket_info_for_passenger_form['queryLeftTicketRequestDTO'][
                'from_station'],
            'toStationTelecode': self.user_ins.ticket_info_for_passenger_form['queryLeftTicketRequestDTO'][
                'to_station'],
            'leftTicket': self.user_ins.ticket_info_for_passenger_form['leftTicketStr'],
            'purpose_codes': self.user_ins.ticket_info_for_passenger_form['purpose_codes'],
            'train_location': self.user_ins.ticket_info_for_passenger_form['train_location'],
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': self.user_ins.global_repeat_submit_token,
        }
        response = self.session.post(API_GET_QUEUE_COUNT, data)
        result = response.json()
        if result.get('data.countT') or result.get('data.ticket'):  # 成功
            """
            "data": { 
                "count": "66",
                "ticket": "0,73", 
                "op_2": "false",
                "countT": "0",
                "op_1": "true"
            }
            """
            ticket = result.get('data.ticket').split(',')  # 暂不清楚具体作用
            ticket_number = sum(map(int, ticket))
            current_position = int(data.get('countT', 0))
            OrderLog.add_quick_log(
                OrderLog.MESSAGE_GET_QUEUE_COUNT_SUCCESS.format(current_position, ticket_number)).flush()
            return True
        else:
            # 加入小黑屋
            OrderLog.add_quick_log(OrderLog.MESSAGE_GET_QUEUE_COUNT_FAIL.format(
                result.get('messages', result.get('validateMessages', '-')))).flush()
        return False

    def confirm_single_for_queue(self):
        """
        确认排队
        passengerTicketStr
        oldPassengerStr
        randCode	
        purpose_codes	00
        key_check_isChange	FEE6C6634A3EAA93E1E6CFC39A99E555A92E438436F18AFF78837CDB
        leftTicketStr	CmDJZYrwUoJ1jFNonIgPzPFdMBvSSE8xfdUwvb2lq8CCWn%2Bzk1vM3roJaHk%3D
        train_location	QY
        choose_seats	
        seatDetailType	000
        whatsSelect	1
        roomType	00
        dwAll	N
        _json_att	
        REPEAT_SUBMIT_TOKEN	0977caf26f25d1da43e3213eb35ff87c
        :return:
        """
        data = {  #
            'passengerTicketStr': self.passenger_ticket_str,
            'oldPassengerStr': self.old_passenger_str,
            'randCode': '',
            'purpose_codes': self.user_ins.ticket_info_for_passenger_form['purpose_codes'],
            'key_check_isChange': self.user_ins.ticket_info_for_passenger_form['key_check_isChange'],
            'leftTicketStr': self.user_ins.ticket_info_for_passenger_form['leftTicketStr'],
            'train_location': self.user_ins.ticket_info_for_passenger_form['train_location'],
            'choose_seats': '',
            'seatDetailType': '000',
            'whatsSelect': '1',
            'roomType': '00',
            'dwAll': 'N',
            '_json_att': '',
            'REPEAT_SUBMIT_TOKEN': self.user_ins.global_repeat_submit_token,
        }

        if self.is_need_auth_code:  # 目前好像是都不需要了，有问题再处理
            pass

        response = self.session.post(API_CONFIRM_SINGLE_FOR_QUEUE, data)
        result = response.json()

        if 'data' in result:
            """
           "data": {
                "submitStatus": true
            }
            """
            if result.get('data.submitStatus'):  # 成功
                OrderLog.add_quick_log(OrderLog.MESSAGE_CONFIRM_SINGLE_FOR_QUEUE_SUCCESS).flush()
                return True
            else:
                # 加入小黑屋 TODO
                OrderLog.add_quick_log(
                    OrderLog.MESSAGE_CONFIRM_SINGLE_FOR_QUEUE_ERROR.format(result.get('data.errMsg', '-'))).flush()
        else:
            OrderLog.add_quick_log(OrderLog.MESSAGE_CONFIRM_SINGLE_FOR_QUEUE_FAIL.format(
                result.get('messages', '-'))).flush()
        return False

    def query_order_wait_time(self):
        """
        排队查询
        random	1546849953542
        tourFlag	dc
        _json_att	
        REPEAT_SUBMIT_TOKEN	0977caf26f25d1da43e3213eb35ff87c
        :return:
        """
        self.current_queue_wait = self.max_queue_wait
        while self.current_queue_wait:
            self.current_queue_wait -= 1
            # TODO 取消超时订单，待优化
            data = {  #
                'random': str(random.random())[2:],
                'tourFlag': 'dc',
                '_json_att': '',
                'REPEAT_SUBMIT_TOKEN': self.user_ins.global_repeat_submit_token,
            }

            response = self.session.get(API_QUERY_ORDER_WAIT_TIME.format(urllib.parse.urlencode(data)))
            result = response.json()

            if result.get('status') and 'data' in result:
                """
               "data": {
                    "queryOrderWaitTimeStatus": true,
                    "count": 0,
                    "waitTime": -1,
                    "requestId": 6487958947291482523,
                    "waitCount": 0,
                    "tourFlag": "dc",
                    "orderId": "E222646122"
                }
                """
                result_data = result['data']
                order_id = result_data.get('orderId')
                if order_id:  # 成功
                    return order_id
                elif result_data.get('waitTime') and result_data.get('waitTime') >= 0:
                    OrderLog.add_quick_log(
                        OrderLog.MESSAGE_QUERY_ORDER_WAIT_TIME_WAITING.format(result_data.get('waitTime'))).flush()
                elif result_data.get('msg'):  # 失败 对不起，由于您取消次数过多，今日将不能继续受理您的订票请求。1月8日您可继续使用订票功能。
                    # TODO 需要增加判断 直接结束
                    OrderLog.add_quick_log(
                        OrderLog.MESSAGE_QUERY_ORDER_WAIT_TIME_FAIL.format(result_data.get('msg', '-'))).flush()
                    stay_second(self.retry_time)
                    return False
            elif result.get('messages') or result.get('validateMessages'):
                OrderLog.add_quick_log(OrderLog.MESSAGE_QUERY_ORDER_WAIT_TIME_FAIL.format(
                    result.get('messages', result.get('validateMessages')))).flush()
            else:
                pass
            OrderLog.add_quick_log(OrderLog.MESSAGE_QUERY_ORDER_WAIT_TIME_INFO.format(self.current_queue_wait)).flush()
            stay_second(self.wait_queue_interval)

        return False

    def make_passenger_ticket_str(self):
        """
        生成提交车次的内容
        格式：
        1(seatType),0,1(车票类型:ticket_type_codes),张三(passenger_name),1(证件类型:passenger_id_type_code),xxxxxx(passenger_id_no),xxxx(mobile_no),N
        passengerTicketStr:
        张三(passenger_name),1(证件类型:passenger_id_type_code),xxxxxx(passenger_id_no),1_
        oldPassengerStr
        :return:
        """
        passenger_tickets = []
        old_passengers = []
        available_passengers = self.query_ins.passengers
        if len(available_passengers) > self.query_ins.member_num_take:  # 删除人数
            available_passengers = available_passengers[0:self.query_ins.member_num_take]
            OrderLog.print_passenger_did_deleted(available_passengers)

        for passenger in available_passengers:
            tmp_str = '{seat_type},0,{passenger_type},{passenger_name},{passenger_id_card_type},{passenger_id_card},{passenger_mobile},N_'.format(
                seat_type=self.query_ins.current_order_seat, passenger_type=passenger['type'],
                passenger_name=passenger['name'],
                passenger_id_card_type=passenger['id_card_type'], passenger_id_card=passenger['id_card'],
                passenger_mobile=passenger['mobile']
            )
            passenger_tickets.append(tmp_str)

            if int(passenger['type']) != UserType.CHILD:
                tmp_old_str = '{passenger_name},{passenger_id_card_type},{passenger_id_card},{passenger_type}_'.format(
                    passenger_name=passenger['name'],
                    passenger_id_card_type=passenger['id_card_type'], passenger_id_card=passenger['id_card'],
                    passenger_type=passenger['type'],
                )
                old_passengers.append(tmp_old_str)

        self.passenger_ticket_str = ''.join(passenger_tickets).rstrip('_')
        self.old_passenger_str = ''.join(old_passengers).rstrip('_') + '__ _ _'  # 不加后面请求会出错
