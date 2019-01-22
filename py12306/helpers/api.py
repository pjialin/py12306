# coding=utf-8
# 查询余票
import time

HOST_URL_OF_12306 = 'kyfw.12306.cn'
BASE_URL_OF_12306 = 'https://' + HOST_URL_OF_12306

LEFT_TICKETS = {
    "url": BASE_URL_OF_12306 + "/otn/{type}?leftTicketDTO.train_date={left_date}&leftTicketDTO.from_station={left_station}&leftTicketDTO.to_station={arrive_station}&purpose_codes=ADULT",
}

API_BASE_LOGIN = {
    "url": BASE_URL_OF_12306 + '/passport/web/login',
}

API_USER_LOGIN_CHECK = BASE_URL_OF_12306 + '/otn/login/conf'

API_AUTH_CODE_DOWNLOAD = {
    'url': BASE_URL_OF_12306 + '/passport/captcha/captcha-image?login_site=E&module=login&rand=sjrand&_={random}'
}
API_AUTH_CODE_BASE64_DOWNLOAD = BASE_URL_OF_12306 + '/passport/captcha/captcha-image64?login_site=E&module=login&rand=sjrand&_={random}'
API_AUTH_CODE_CHECK = {
    'url': BASE_URL_OF_12306 + '/passport/captcha/captcha-check?answer={answer}&rand=sjrand&login_site=E&_={random}'
}
API_AUTH_UAMTK = {
    'url': BASE_URL_OF_12306 + '/passport/web/auth/uamtk'
}
API_AUTH_UAMAUTHCLIENT = {
    'url': BASE_URL_OF_12306 + '/otn/uamauthclient'
}

API_USER_INFO = {
    'url': BASE_URL_OF_12306 + '/otn/modifyUser/initQueryUserInfoApi'
}
API_USER_PASSENGERS = BASE_URL_OF_12306 + '/otn/confirmPassenger/getPassengerDTOs'
API_SUBMIT_ORDER_REQUEST = BASE_URL_OF_12306 + '/otn/leftTicket/submitOrderRequest'
API_CHECK_ORDER_INFO = BASE_URL_OF_12306 + '/otn/confirmPassenger/checkOrderInfo'
API_INITDC_URL = BASE_URL_OF_12306 + '/otn/confirmPassenger/initDc'  # 生成订单时需要先请求这个页面
API_GET_QUEUE_COUNT = BASE_URL_OF_12306 + '/otn/confirmPassenger/getQueueCount'
API_CONFIRM_SINGLE_FOR_QUEUE = BASE_URL_OF_12306 + '/otn/confirmPassenger/confirmSingleForQueue'
API_QUERY_ORDER_WAIT_TIME = BASE_URL_OF_12306 + '/otn/confirmPassenger/queryOrderWaitTime?{}'  # 排队查询

API_NOTIFICATION_BY_VOICE_CODE = 'http://ali-voice.showapi.com/sendVoice?'
API_NOTIFICATION_BY_VOICE_CODE_DINGXIN = 'http://yuyin2.market.alicloudapi.com/dx/voice_notice'

API_FREE_CODE_QCR_API = 'http://60.205.200.159/api'
API_FREE_CODE_QCR_API_CHECK = 'http://check.huochepiao.360.cn/img_vcode'

API_CHECK_CDN_AVAILABLE = 'https://{}/otn/dynamicJs/omseuuq'
