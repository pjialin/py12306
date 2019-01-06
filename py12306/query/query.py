from requests_html import HTMLSession

import py12306.config as config
from py12306.helpers.api import LEFT_TICKETS
from py12306.helpers.func import *
from py12306.helpers.station import Station
from py12306.log.query_log import QueryLog
from py12306.query.job import Job


class Query:
    """
    余票查询

    """
    jobs = []
    session = {}

    def __init__(self):
        self.session = HTMLSession()

    @classmethod
    def run(cls):
        self = cls()
        self.start()
        pass

    def start(self):
        self.init_jobs()
        QueryLog.print_init_jobs(jobs=self.jobs).flush()
        for job in self.jobs:
            self.handle_single_job(job)

    def init_jobs(self):
        jobs = config.QUERY_JOBS
        for job in jobs:
            job = Job(info=job)
            self.jobs.append(job)

    def handle_single_job(self, job):
        """
        处理单个任务
        根据日期循环查询

        展示处理时间
        :param job:
        :return:
        """
        for date in job.left_dates:
            result = self.query_by_job_and_date(job, date)
            self.handle_single_result(result)

        station = Station.get_station_by_name('广州')
        print(station)
        pass

    def query_by_job_and_date(self, job, date):
        """
        通过日期进行查询
        :return:
        """
        QueryLog.add_log('正在查询 {}, {} - {}'.format(date, job.left_station, job.arrive_station))
        url = LEFT_TICKETS.get('url').format(left_date=date, left_station=job.left_station_code,
                                             arrive_station=job.arrive_station_code, type='leftTicket/queryZ')

        return self.session.get(url)

    def handle_single_result(self, result):
        """
        错误判断
        余票判断
        小黑屋判断
        座位判断
        乘车人判断
        :param result:
        :return:
        """
        pass
