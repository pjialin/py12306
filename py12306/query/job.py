from py12306.helpers.station import Station


class Job:
    """
    查询任务
    """

    left_dates = []
    left_station = ''
    arrive_station = ''
    left_station_code = ''
    arrive_station_code = ''

    allow_seats = []
    allow_train_numbers = []
    members = []
    member_num = []


    def __init__(self, info):
        self.left_dates = info.get('left_dates')
        self.left_station = info.get('stations').get('left')
        self.arrive_station = info.get('stations').get('arrive')
        self.left_station_code = Station.get_station_key_by_name(self.left_station)
        self.arrive_station_code = Station.get_station_key_by_name(self.arrive_station)

        self.allow_seats = info.get('seats')
        self.allow_train_numbers = info.get('train_numbers')
        self.members = info.get('members')
        self.member_num = len(self.members)
