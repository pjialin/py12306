import urllib

# from py12306.config import UserType
from py12306.config import Config
from py12306.helpers.api import *
from py12306.helpers.func import *
from py12306.helpers.notification import Notification
from py12306.helpers.type import UserType, SeatType
from py12306.log.common_log import CommonLog
from py12306.log.order_log import OrderLog


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

    max_queue_wait = 60 * 5  # 最大排队时长
    current_queue_wait = 0
    retry_time = 3
    wait_queue_interval = 3

    order_id = 0

    notification_sustain_time = 60 * 30  # 通知持续时间 30 分钟
    notification_interval = 5 * 60  # 通知间隔

    def __init__(self, query, user):
        self.session = user.session
        from py12306.query.job import Job
        from py12306.user.job import UserJob
        assert isinstance(query, Job)
        assert isinstance(user, UserJob)
        self.query_ins = query
        self.user_ins = user

        self.make_passenger_ticket_str()

    def order(self):
        """
        开始下单
        下单模式  暂时不清楚，使用正常步骤下单
        :return:
        """
        # Debug
        if Config().IS_DEBUG:
            self.order_id = 'test'
            self.order_did_success()
            return random.randint(0, 10) > 7
        return self.normal_order()

    def normal_order(self):
        order_request_res = self.submit_order_request()
        if order_request_res == -1:
            return self.order_did_success()
        elif not order_request_res:
            return
        if not self.user_ins.request_init_dc_page(): return
        if not self.check_order_info(): return
        if not self.get_queue_count(): return
        if not self.confirm_single_for_queue(): return
        order_id = self.query_order_wait_time()
        if order_id:  # 发送通知
            self.order_id = order_id
            self.order_did_success()
            return True
        return False

    def order_did_success(self):
        OrderLog.print_ticket_did_ordered(self.order_id)
        OrderLog.notification(OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_TITLE,
                              OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_CONTENT.format(self.user_ins.user_name))
        self.send_notification()
        return True

    def send_notification(self):
        # num = 0  # 通知次数
        # sustain_time = self.notification_sustain_time
        info_message = OrderLog.get_order_success_notification_info(self.query_ins)
        normal_message = OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_OF_EMAIL_CONTENT.format(self.order_id, self.user_ins.user_name)
        if Config().EMAIL_ENABLED:  # 邮件通知
            Notification.send_email(Config().EMAIL_RECEIVER, OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_TITLE,
                                    normal_message + info_message)
        if Config().DINGTALK_ENABLED:  # 钉钉通知
            Notification.dingtalk_webhook(normal_message + info_message)
        if Config().TELEGRAM_ENABLED:  # Telegram推送
            Notification.send_to_telegram(normal_message + info_message)
        if Config().SERVERCHAN_ENABLED:  # ServerChan通知
            Notification.server_chan(Config().SERVERCHAN_KEY, OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_TITLE,
                                     normal_message + info_message)
        if Config().PUSHBEAR_ENABLED:  # PushBear通知
            Notification.push_bear(Config().PUSHBEAR_KEY, OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_TITLE,
                                   normal_message + info_message)

        if Config().NOTIFICATION_BY_VOICE_CODE:  # 语音通知
            if Config().NOTIFICATION_VOICE_CODE_TYPE == 'dingxin':
                voice_info = {
                    'left_station': self.query_ins.left_station,
                    'arrive_station': self.query_ins.arrive_station,
                    'set_type': self.query_ins.current_seat_name,
                    'orderno': self.order_id
                }
            else:
                voice_info = OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_OF_VOICE_CODE_CONTENT.format(
                    self.query_ins.left_station, self.query_ins.arrive_station)
            OrderLog.add_quick_log(OrderLog.MESSAGE_ORDER_SUCCESS_NOTIFICATION_OF_VOICE_CODE_START_SEND)
            Notification.voice_code(Config().NOTIFICATION_VOICE_CODE_PHONE, self.user_ins.get_name(), voice_info)
        # 取消循环发送通知
        # while sustain_time:  # TODO 后面直接查询有没有待支付的订单就可以
        #     num += 1
        #     else:
        #         break
        #     sustain_time -= self.notification_interval
        #     sleep(self.notification_interval)

        OrderLog.add_quick_log(OrderLog.MESSAGE_JOB_CLOSED).flush()
        return True

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
                # 0125 增加排队时长到 5 分钟之后，更多的是 排队失败，得通过拿到订单列表才能确认，再打个 TODO
                # self.order_id = 0  # 需要拿到订单号 TODO
                # return -1
                pass
            OrderLog.add_quick_log(
                OrderLog.MESSAGE_SUBMIT_ORDER_REQUEST_FAIL.format(
                    result.get('messages', CommonLog.MESSAGE_RESPONSE_EMPTY_ERROR))).flush()
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
            # ifShowPassCode 需要验证码
            OrderLog.add_quick_log(OrderLog.MESSAGE_CHECK_ORDER_INFO_SUCCESS).flush()
            if result.get('data.ifShowPassCode') != 'N':
                self.is_need_auth_code = True

            # if ( ticketInfoForPassengerForm.isAsync == ticket_submit_order.request_flag.isAsync & & ticketInfoForPassengerForm.queryLeftTicketRequestDTO.ypInfoDetail != "") { 不需要排队检测 js TODO
            return True
        else:
            error = CommonLog.MESSAGE_API_RESPONSE_CAN_NOT_BE_HANDLE
            if not result.get('data.isNoActive'):
                error = result.get('data.errMsg', CommonLog.MESSAGE_RESPONSE_EMPTY_ERROR)
            else:
                if result.get('data.checkSeatNum'):
                    error = '无法提交您的订单! ' + result.get('data.errMsg')
                else:
                    error = '出票失败! ' + result.get('data.errMsg')
            OrderLog.add_quick_log(OrderLog.MESSAGE_CHECK_ORDER_INFO_FAIL.format(error)).flush()
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
                datetime.datetime.strptime(self.query_ins.left_date, '%Y-%m-%d').strftime("%a %h %d %Y")),
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
        if result.get('status', False):  # 成功
            """
            "data": { 
                "count": "66",
                "ticket": "0,73", 
                "op_2": "false",
                "countT": "0",
                "op_1": "true"
            }
            
            """
            # if result.get('isRelogin') == 'Y': # 重新登录 TODO

            ticket = result.get('data.ticket').split(',')  # 余票列表
            # 这里可以判断 是真实是 硬座还是无座，避免自动分配到无座
            ticket_number = ticket[0]  # 余票
            if ticket_number != '充足' and int(ticket_number) <= 0:
                if self.query_ins.current_seat == SeatType.NO_SEAT:  # 允许无座
                    ticket_number = ticket[1]
                if not int(ticket_number): # 跳过无座
                    OrderLog.add_quick_log(OrderLog.MESSAGE_GET_QUEUE_INFO_NO_SEAT).flush()
                    return False

            if result.get('data.op_2') == 'true':
                OrderLog.add_quick_log(OrderLog.MESSAGE_GET_QUEUE_LESS_TICKET).flush()
                return False

            current_position = int(result.get('data.countT', 0))
            OrderLog.add_quick_log(
                OrderLog.MESSAGE_GET_QUEUE_INFO_SUCCESS.format(current_position, ticket_number)).flush()
            return True
        else:
            # 加入小黑屋
            OrderLog.add_quick_log(OrderLog.MESSAGE_GET_QUEUE_COUNT_FAIL.format(
                result.get('messages', result.get('validateMessages', CommonLog.MESSAGE_RESPONSE_EMPTY_ERROR)))).flush()
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
                    OrderLog.MESSAGE_CONFIRM_SINGLE_FOR_QUEUE_ERROR.format(
                        result.get('data.errMsg', CommonLog.MESSAGE_RESPONSE_EMPTY_ERROR))).flush()
        else:
            OrderLog.add_quick_log(OrderLog.MESSAGE_CONFIRM_SINGLE_FOR_QUEUE_FAIL.format(
                result.get('messages', CommonLog.MESSAGE_RESPONSE_EMPTY_ERROR))).flush()
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
        self.queue_num = 0
        while self.current_queue_wait:
            self.current_queue_wait -= self.wait_queue_interval
            self.queue_num += 1
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
                elif 'waitTime' in result_data:
                    # 计算等待时间
                    wait_time = int(result_data.get('waitTime'))
                    if wait_time == -1 or wait_time == -100:  # 成功
                        # /otn/confirmPassenger/resultOrderForDcQueue 请求订单状态 目前不需要
                        # 不应该走到这
                        return order_id
                    elif wait_time >= 0:  # 等待
                        OrderLog.add_quick_log(
                            OrderLog.MESSAGE_QUERY_ORDER_WAIT_TIME_WAITING.format(result_data.get('waitCount', 0),
                                                                                  wait_time)).flush()
                    else:
                        if wait_time == -2 or wait_time == -3:  # -2 失败 -3 订单已撤销
                            OrderLog.add_quick_log(
                                OrderLog.MESSAGE_QUERY_ORDER_WAIT_TIME_FAIL.format(result_data.get('msg'))).flush()
                            return False
                        else:  # 未知原因
                            OrderLog.add_quick_log(
                                OrderLog.MESSAGE_QUERY_ORDER_WAIT_TIME_FAIL.format(
                                    result_data.get('msg', wait_time))).flush()
                            return False

                elif result_data.get('msg'):  # 失败 对不起，由于您取消次数过多，今日将不能继续受理您的订票请求。1月8日您可继续使用订票功能。
                    # TODO 需要增加判断 直接结束
                    OrderLog.add_quick_log(
                        OrderLog.MESSAGE_QUERY_ORDER_WAIT_TIME_FAIL.format(
                            result_data.get('msg', CommonLog.MESSAGE_RESPONSE_EMPTY_ERROR))).flush()
                    stay_second(self.retry_time)
                    return False
            elif result.get('messages') or result.get('validateMessages'):
                OrderLog.add_quick_log(OrderLog.MESSAGE_QUERY_ORDER_WAIT_TIME_FAIL.format(
                    result.get('messages', result.get('validateMessages')))).flush()
                return False
            else:
                pass
            OrderLog.add_quick_log(OrderLog.MESSAGE_QUERY_ORDER_WAIT_TIME_INFO.format(self.queue_num)).flush()
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
