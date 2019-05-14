from os import path

from py12306.config import Config
from py12306.helpers.func import *


@singleton
class Station:
    stations = []
    station_kvs = {}

    def __init__(self):
        if path.exists(Config().STATION_FILE):
            result = open(Config().STATION_FILE, encoding='utf-8').read()
            result = result.lstrip('@').split('@')
            for i in result:
                tmp_info = i.split('|')
                self.stations.append({
                    'key': tmp_info[2],
                    'name': tmp_info[1],
                    'pinyin': tmp_info[3],
                    'id': tmp_info[5]
                })
                self.station_kvs[tmp_info[1]] = tmp_info[2]

    @classmethod
    def get_station_by_name(cls, name):
        return cls.get_station_by(name, 'name')

    @classmethod
    def get_station_by(cls, value, field):
        self = cls()
        for station in self.stations:
            if station.get(field) == value:
                return station
        return None

    @classmethod
    def get_station_key_by_name(cls, name):
        self = cls()
        return self.station_kvs[name]

    @classmethod
    def get_station_name_by_key(cls, key):
        return cls.get_station_by(key, 'key').get('name')

