HOST_API = 'kyfw.12306.cn'
BASE_API = 'https://' + HOST_API

# LEFT_TICKETS = {
#     "url": BASE_URL_OF_12306 + "/otn/{type}?leftTicketDTO.train_date={left_date}&leftTicketDTO.from_station={left_station}&leftTicketDTO.to_station={arrive_station}&purpose_codes=ADULT",
# }


API_QUERY_INIT_PAGE = BASE_API + '/otn/leftTicket/init'
API_LEFT_TICKETS = BASE_API + '/otn/{type}?leftTicketDTO.train_date={left_date}&leftTicketDTO.from_station={' \
                          'left_station}&leftTicketDTO.to_station={arrive_station}&purpose_codes=ADULT'
