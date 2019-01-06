import json
from os import path
from py12306.log.base import BaseLog
from py12306.helpers.func import *


@singleton
class QueryLog(BaseLog):
    data = {
        'query_count': 0,
        'last_time': '',
    }

    LOG_INIT_JOBS = ''

    def __init__(self):
        super().__init__()
        self.init_data()

    def init_data(self):
        # 获取上次记录
        print('Query Log 初始化')
        file_path = config.QUERY_DATA_DIR + '/status.json'
        if path.exists(file_path):
            result = open(file_path, encoding='utf-8').read()
            if result:
                result = json.loads(result)
                self.data = {**self.data, **result}

    @classmethod
    def print_init_jobs(cls, jobs):
        self = cls()
        """
        输出初始化信息
        :return:
        """
        self.add_log('# 发现任务 {} 条 #'.format(len(jobs)))
        index = 1
        for job in jobs:
            self.add_log('================== 任务 {} =================='.format(index))
            self.add_log('出发站：{}    到达站：{}'.format(job.left_station, job.arrive_station))
            self.add_log('乘车日期：{}'.format(job.left_dates))
            self.add_log('坐席：{}'.format('，'.join(job.allow_seats)))
            self.add_log('乘车人：{}'.format('，'.join(job.members)))
            self.add_log('筛选车次：{}'.format('，'.join(job.allow_train_numbers)))
            # 乘车日期：['2019-01-24', '2019-01-25', '2019-01-26', '2019-01-27']
            index += 1

        return self
