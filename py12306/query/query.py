import threading


from py12306.helpers.app import app_available_check
from py12306.helpers.func import *
from py12306.helpers.request import Request
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
        self.session = Request()

    @classmethod
    def run(cls):
        self = cls()
        app_available_check()
        self.start()
        pass

    def start(self):
        # return # DEBUG
        self.init_jobs()
        QueryLog.print_init_jobs(jobs=self.jobs)
        stay_second(1)

        while True:
            app_available_check()
            if config.QUERY_JOB_THREAD_ENABLED:  # 多线程
                create_thread_and_run(jobs=self.jobs, callback_name='run')
            else:
                for job in self.jobs:
                    job.run()
            if Const.IS_TEST: return

    def init_jobs(self):
        jobs = config.QUERY_JOBS
        for job in jobs:
            job = Job(info=job, query=self)
            self.jobs.append(job)
