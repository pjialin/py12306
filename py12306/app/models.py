import datetime
import random
import string
import urllib
from typing import List

from tortoise import Model, fields

from lib.exceptions import LoadConfigFailException
from lib.helper import json_friendly_loads, json_friendly_dumps, StationHelper


class TimestampMixin:
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)


class BaseModel(Model):
    id = fields.IntField(pk=True)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        if hasattr(self, 'hash_id'):
            self.hash_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=16))

    class Meta:
        abstract = True

    async def refresh_from_db(self):
        new = await self.__class__.filter(id=self.id).first()
        self.__dict__.update(new.__dict__)

    @classmethod
    async def get_or_create_instance(cls, **kwargs):
        ret = await cls.filter(**kwargs).first()
        if not ret:
            ret = cls()
            for k, v in kwargs.items():
                setattr(ret, k, v)
        return ret


class FriendlyJSONField(fields.JSONField):

    def __init__(self, **kwargs) -> None:
        super().__init__(encoder=json_friendly_dumps, decoder=json_friendly_loads, **kwargs)


class QueryJob(TimestampMixin, BaseModel):
    """ 查询任务 """

    class Status:
        Normal = 'normal'
        WaitVerify = 'wait_verify'
        Finished = 'finished'
        Error = 'error'

    hash_id = fields.CharField(max_length=16, default='', index=True, description='Hash')
    user = fields.ForeignKeyField('models.User', on_delete=fields.SET_NULL, null=True)
    name = fields.CharField(max_length=255, default='', description='任务名称')
    left_dates = FriendlyJSONField(default=[], description='出发日期')
    left_date = fields.DateField(default=None, null=True, description='当前出发日期')
    stations = FriendlyJSONField(default=[], description='查询车站')
    left_station = fields.CharField(max_length=255, default='', description='出发地')
    arrive_station = fields.CharField(max_length=255, default='', description='到达地')
    left_periods = FriendlyJSONField(default={}, description='出发时间')
    allow_train_numbers = FriendlyJSONField(default=[], description='筛选车次')
    execpt_train_numbers = FriendlyJSONField(default=[], description='筛选车次(反')
    allow_seats = FriendlyJSONField(default=[], description='筛选座位')
    members = FriendlyJSONField(default=[], description='乘车人员')
    member_num = fields.SmallIntField(default=0, description='人员数量')
    query_num = fields.IntField(default=0, description='查询次数')
    less_member = fields.BooleanField(default=False, description='提交部分乘客')
    status = fields.CharField(max_length=20, default=Status.WaitVerify, index=True, description='任务状态')
    enable = fields.BooleanField(default=True, description='启用状态')
    passengers = FriendlyJSONField(default={}, description='乘客列表')
    last_process_at = fields.DatetimeField(default=None, null=True, description='最后一次执行')
    last_error = fields.CharField(default='', max_length=500, description='最后一次错误')

    class Meta:
        table = 'query_jobs'

    @property
    def is_queryable(self) -> bool:
        """ 验证任务是否可查询 有一个可用即可"""
        for left_date in self.left_dates:
            if left_date < datetime.datetime.now().date():
                continue
            if left_date > (datetime.datetime.now().date() + datetime.timedelta(days=31)):
                continue
            return True
        return False

    @property
    def current_is_queryable(self) -> bool:
        """ 验证当前任务是否可查询"""
        if self.left_date < datetime.datetime.now().date():
            return False
        if self.left_date > (datetime.datetime.now().date() + datetime.timedelta(days=30)):
            return False
        return True

    @property
    def query_num_next(self) -> int:
        self.query_num += 1
        return self.query_num

    @classmethod
    def filter_available(cls):
        return cls.filter(enable=True, status=QueryJob.Status.Normal)

    @property
    def name_text(self):
        """ 任务名称  """
        return f'ID {self.id} {self.name or self.route_time_text}'.strip()

    @property
    def route_text(self):
        """ 行程文本 北京 - 深圳，北京 — 广州 """
        return '，'.join([f'{station[0]} - {station[1]}' for station in self.stations])

    @property
    def current_route_text(self) -> str:
        """ 行程文本 北京 - 深圳 """
        return f'{self.left_station} - {self.arrive_station}'

    @property
    def left_time_text(self):
        """ 出发时间文本 2020-01-05，2020-01-06 """
        return '，'.join([str(left_date) for left_date in self.left_dates])

    @property
    def route_time_text(self):
        """ 路程与时间信息 """
        return f'{self.route_text} 出发时间 {self.left_time_text}'

    @property
    def left_station_id(self):
        return StationHelper.id_by_cn(self.left_station)

    @property
    def arrive_station_id(self):
        return StationHelper.id_by_cn(self.arrive_station)

    @property
    def is_available(self):
        return self.enable and self.status == self.Status.Normal

    @property
    def is_alive(self) -> bool:
        return self.last_process_at and (datetime.datetime.now() - self.last_process_at).seconds < 30

    async def update_last_process_at(self) -> datetime.datetime:
        self.last_process_at = datetime.datetime.now()
        await self.save()
        return self.last_process_at

    @classmethod
    async def load_from_config(cls, config: dict):
        if not config.get('id'):
            raise LoadConfigFailException('未指定查询任务 ID')
        user, user_id = None, config.get('user_id')
        if user_id:
            user = await User.filter(id=user_id).first()
            if not user:
                raise LoadConfigFailException(f'未找到查询订单关联用户 id {user_id}')
        else:
            user_id = None
        query = await cls.get_or_create_instance(id=config['id'])
        stations = config.get('stations', [])
        members = config.get('members', [])
        periods = config.get('periods', [])
        # 验证时间筛选
        if periods and len(periods) is not 2:
            raise LoadConfigFailException(f'乘车时间区间验证失败 {periods}')
        # 验证查询车站
        if not len(stations) or len(stations) % 2 is not 0:
            raise LoadConfigFailException('查询车站配置验证失败')
        stations = [stations[i:i + 2] for i in range(0, len(stations), 2)]
        for station in stations:
            if not StationHelper.id_by_cn(station[0]) or not StationHelper.id_by_cn(station[1]):
                raise LoadConfigFailException(f'未找到该车站 {station}')
        if not len(members):
            raise LoadConfigFailException('乘车人员验证失败')
        # 验证乘车时间
        left_dates_str_list = config.get('left_dates', [])
        if not left_dates_str_list:
            raise LoadConfigFailException('乘车日期验证失败')
        left_dates = []
        for left_date_str in left_dates_str_list:
            try:
                left_dates.append(datetime.datetime.strptime(left_date_str, '%Y-%m-%d').date())
            except Exception:
                raise LoadConfigFailException(f'乘车日期格式验证失败 {left_date_str}')

        query.enable = config.get('enable', True)
        if query.user_id is not user_id:  # 恢复为待验证状态
            query.status = query.Status.WaitVerify
        query.user_id = user_id or query.user_id
        query.allow_seats = config.get('seats', [])
        query.allow_train_numbers = list(map(str.upper, config.get('train_numbers', [])))
        query.execpt_train_numbers = list(
            map(str.upper, config.get('except_train_numbers', [])))
        query.left_periods = periods or query.left_periods
        query.members = members
        query.member_num = len(query.members)
        query.left_dates = left_dates
        query.stations = stations
        await query.save()
        return query


class Ticket(TimestampMixin, BaseModel):
    """ Ticket """
    hash_id = fields.CharField(max_length=16, default='', index=True, description='Hash')
    left_date = fields.DateField(default=None, null=True)
    ticket_num = fields.CharField(default='', max_length=255, description='余票数量')
    train_number = fields.CharField(default='', max_length=255)
    train_no = fields.CharField(default='', max_length=255)
    left_station = fields.CharField(default='', max_length=255)
    arrive_station = fields.CharField(default='', max_length=255)
    order_text = fields.CharField(default='', max_length=255)
    secret_str = fields.CharField(default='', max_length=1000)
    left_time = fields.CharField(default='', max_length=255)
    arrive_time = fields.CharField(default='', max_length=255)
    # { 'name': seat, 'id': seat_id, 'raw': raw, 'order_id': TrainSeat.order_id[seat] }
    available_seat = FriendlyJSONField(default=[], description='可用座位')
    member_num_take = fields.SmallIntField(default=0, description='实际人员数量')
    raw = FriendlyJSONField(default={})

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    class Meta:
        table = 'tickets'

    @property
    def left_date_order(self):
        return self.left_date.strftime('%Y-%m-%d')

    @property
    def secret_str_unquote(self) -> str:
        return urllib.parse.unquote(self.secret_str)

    @classmethod
    def parse_tickets_text(cls, tickts: List[str]):
        ret = []
        for tickt_str in tickts:
            ticket = cls.from_ticket_text(tickt_str)
            ret.append(ticket)
        return ret

    @property
    def baby(self):
        """ 小黑屋 ID """
        return f"{self.left_date}_{self.train_number}_{self.available_seat.get('id')}"

    @property
    def route_text(self):
        """ 行程文本 北京 - 深圳 """
        return f'{self.left_station} - {self.arrive_station}'

    @property
    def detail_text(self):
        """ 车次详细信息 车次 G335 时间 23:15 - 14:25 硬卧 余票 10 """
        return f"车次 {self.train_number} 时间 {self.left_date} {self.left_time} - {self.arrive_time} {self.available_seat.get('name')} 余票 {self.ticket_num}"

    @property
    def dark_room_text(self):
        """ 小黑屋信息 车次 G335 时间 2020-01-20 硬卧 """
        return f"车次 {self.train_number} 时间 {self.left_date} {self.available_seat.get('name')}"

    @classmethod
    def from_ticket_text(cls, ticket_str):
        info = ticket_str.split('|')
        ticket = Ticket()
        ticket.left_date = datetime.datetime.strptime(info[13], '%Y%m%d').date()
        ticket.train_no = info[2]
        ticket.ticket_num = info[11]
        ticket.train_number = info[3]
        ticket.left_station = info[6]
        ticket.arrive_station = info[7]
        ticket.order_text = info[1]
        ticket.secret_str = info[0]
        ticket.left_time = info[8]
        ticket.arrive_time = info[9]
        ticket.raw = info
        return ticket


class User(TimestampMixin, BaseModel):
    """ 12306 用户 """

    user_id = fields.CharField(default='', max_length=50, description='12306 ID')
    name = fields.CharField(default='', max_length=255, description='用户名')
    password = fields.CharField(default='', max_length=255, description='密码')
    real_name = fields.CharField(default='', max_length=255, description='姓名')
    last_heartbeat = fields.DatetimeField(default=None, null=True, description='上次心跳')
    last_cookies = fields.TextField(default=None, null=True, description='上次 Cookie')
    passengers = FriendlyJSONField(default={}, description='乘客列表')
    enable = fields.BooleanField(default=True, description='启用状态')
    last_process_at = fields.DatetimeField(default=None, null=True, description='最后一次执行')

    class Meta:
        table = 'users'

    @property
    def is_alive(self) -> bool:
        return self.last_process_at and (datetime.datetime.now() - self.last_process_at).seconds < 60

    @property
    def name_text(self) -> str:
        """ 任务名称  """
        return f'ID {self.id} {self.user_id}'

    async def update_last_process_at(self) -> datetime.datetime:
        self.last_process_at = datetime.datetime.now()
        await self.save()
        return self.last_process_at

    @classmethod
    async def load_from_config(cls, config: dict):
        if not config.get('id'):
            raise LoadConfigFailException('未指定用户 ID')
        user = await cls.get_or_create_instance(id=config['id'])
        user.enable = config.get('enable', True)
        user.name = config.get('name', '')
        user.password = config.get('password')
        await user.save()
        return user


class Order(TimestampMixin, BaseModel):
    """ 订单 """

    class Status:
        Wait = 'wait'
        DarkRoom = 'dark_room'  # 小黑屋
        Error = 'error'
        Success = 'success'

    user = fields.ForeignKeyField('models.User', on_delete=fields.SET_NULL, null=True)
    query_job = fields.ForeignKeyField('models.QueryJob', on_delete=fields.SET_NULL, null=True)
    ticket = fields.ForeignKeyField('models.Ticket', on_delete=fields.SET_NULL, null=True)
    status = fields.CharField(max_length=20, default=Status.Wait, index=True, description='任务状态')
    last_error = fields.CharField(default='', max_length=500, description='最后一次错误')

    class Meta:
        table = 'orders'
