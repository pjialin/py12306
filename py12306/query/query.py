import threading

from requests_html import HTMLSession

from py12306.helpers.func import *
from py12306.log.query_log import QueryLog
from py12306.query.job import Job


class Query:
    """
    余票查询

    """
    jobs = []
    session = {}

    # 查询间隔
    interval = {}

    def __init__(self):
        self.interval = init_interval_by_number(config.QUERY_INTERVAL)
        self.session = HTMLSession()

    @classmethod
    def run(cls):
        self = cls()
        self.start()
        pass

    def start(self):
        self.init_jobs()
        QueryLog.print_init_jobs(jobs=self.jobs)
        while True:
            threads = []
            if config.QUERY_JOB_THREAD_ENABLED:  # 多线程
                for job in self.jobs:
                    thread = threading.Thread(target=job.run)
                    thread.start()
                    threads.append(thread)
                for thread in threads:
                    thread.join()
            else:
                for job in self.jobs:
                    job.run()

    def init_jobs(self):
        jobs = config.QUERY_JOBS
        for job in jobs:
            job = Job(info=job, query=self)
            self.jobs.append(job)
