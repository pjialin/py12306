from py12306.config import Config
from py12306.cluster.cluster import Cluster
from py12306.app import app_available_check
from py12306.helpers.func import *
from py12306.helpers.request import Request
from py12306.log.query_log import QueryLog
from py12306.query.job import Job


@singleton
class Query:
    """
    余票查询

    """
    jobs = []
    query_jobs = []
    session = {}

    # 查询间隔
    interval = {}
    cluster = None

    def __init__(self):
        self.session = Request()
        self.cluster = Cluster()
        self.update_query_interval()
        self.update_query_jobs()

    def update_query_interval(self, auto=False):
        self.interval = init_interval_by_number(Config().QUERY_INTERVAL)

    def update_query_jobs(self, auto=False):
        self.query_jobs = Config().QUERY_JOBS
        if auto:
            self.jobs = []
            QueryLog.add_quick_log(QueryLog.MESSAGE_JOBS_DID_CHANGED).flush()
            self.init_jobs()

    @classmethod
    def run(cls):
        self = cls()
        app_available_check()
        self.start()
        pass

    def start(self):
        # return # DEBUG
        self.init_jobs()
        QueryLog.init_data()
        stay_second(1)
        while True:
            app_available_check()
            if Config().QUERY_JOB_THREAD_ENABLED:  # 多线程
                create_thread_and_run(jobs=self.jobs, callback_name='run')
            else:
                for job in self.jobs: job.run()
            if Const.IS_TEST: return
            # self.refresh_jobs()  # 刷新任务

    def init_jobs(self):
        for job in self.query_jobs:
            job = Job(info=job, query=self)
            self.jobs.append(job)
        QueryLog.print_init_jobs(jobs=self.jobs)

    # def get_jobs_from_cluster(self):
    #     jobs = self.cluster.session.get_dict(Cluster.KEY_JOBS)
    #     return jobs
    #
    # def update_jobs_of_cluster(self):
    #     if config.CLUSTER_ENABLED and config.NODE_IS_MASTER:
    #         return self.cluster.session.set_dict(Cluster.KEY_JOBS, self.query_jobs)
    #
    # def refresh_jobs(self):
    #     if not config.CLUSTER_ENABLED: return
    #     jobs = self.get_jobs_from_cluster()
    #     if jobs != self.query_jobs:
    #         self.jobs = []
    #         self.query_jobs = jobs
    #         QueryLog.add_quick_log(QueryLog.MESSAGE_JOBS_DID_CHANGED).flush()
    #         self.init_jobs()
