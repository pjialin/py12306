from base64 import b64decode
from py12306.config import Config
from py12306.cluster.cluster import Cluster
from py12306.app import app_available_check
from py12306.helpers.func import *
from py12306.helpers.request import Request
from py12306.log.query_log import QueryLog
from py12306.query.job import Job
from py12306.helpers.api import API_QUERY_INIT_PAGE, API_GET_BROWSER_DEVICE_ID


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

    is_in_thread = False
    retry_time = 3
    is_ready = False
    api_type = None  # Query api url, Current know value  leftTicket/queryX | leftTicket/queryZ

    def __init__(self):
        self.session = Request()
        self.request_device_id()
        self.cluster = Cluster()
        self.update_query_interval()
        self.update_query_jobs()
        self.get_query_api_type()

    def update_query_interval(self, auto=False):
        self.interval = init_interval_by_number(Config().QUERY_INTERVAL)
        if auto:
            jobs_do(self.jobs, 'update_interval')

    def update_query_jobs(self, auto=False):
        self.query_jobs = Config().QUERY_JOBS
        if auto:
            QueryLog.add_quick_log(QueryLog.MESSAGE_JOBS_DID_CHANGED).flush()
            self.refresh_jobs()
            if not Config().is_slave():
                jobs_do(self.jobs, 'check_passengers')

    @classmethod
    def run(cls):
        self = cls()
        app_available_check()
        self.start()
        pass

    @classmethod
    def check_before_run(cls):
        self = cls()
        self.init_jobs()
        self.is_ready = True

    def start(self):
        # return # DEBUG
        QueryLog.init_data()
        stay_second(3)
        # 多线程
        while True:
            if Config().QUERY_JOB_THREAD_ENABLED:  # 多线程
                if not self.is_in_thread:
                    self.is_in_thread = True
                    create_thread_and_run(jobs=self.jobs, callback_name='run', wait=Const.IS_TEST)
                if Const.IS_TEST: return
                stay_second(self.retry_time)
            else:
                if not self.jobs: break
                self.is_in_thread = False
                jobs_do(self.jobs, 'run')
                if Const.IS_TEST: return

        # while True:
        #     app_available_check()
        #     if Config().QUERY_JOB_THREAD_ENABLED:  # 多线程
        #         create_thread_and_run(jobs=self.jobs, callback_name='run')
        #     else:
        #         for job in self.jobs: job.run()
        #     if Const.IS_TEST: return
        # self.refresh_jobs()  # 刷新任务

    def refresh_jobs(self):
        """
        更新任务
        :return:
        """
        allow_jobs = []
        for job in self.query_jobs:
            id = md5(job)
            job_ins = objects_find_object_by_key_value(self.jobs, 'id', id)  # [1 ,2]
            if not job_ins:
                job_ins = self.init_job(job)
                if Config().QUERY_JOB_THREAD_ENABLED:  # 多线程重新添加
                    create_thread_and_run(jobs=job_ins, callback_name='run', wait=Const.IS_TEST)
            allow_jobs.append(job_ins)

        for job in self.jobs:  # 退出已删除 Job
            if job not in allow_jobs: job.destroy()

        QueryLog.print_init_jobs(jobs=self.jobs)

    def init_jobs(self):
        for job in self.query_jobs:
            self.init_job(job)
        QueryLog.print_init_jobs(jobs=self.jobs)

    def init_job(self, job):
        job = Job(info=job, query=self)
        self.jobs.append(job)
        return job

    def request_device_id(self, force_renew = False):
        """
        获取加密后的浏览器特征 ID
        :return:
        """
        expire_time =  self.session.cookies.get('RAIL_EXPIRATION')
        if not force_renew and expire_time and int(expire_time) - time_int_ms() > 0:
            return
        if 'pjialin' not in API_GET_BROWSER_DEVICE_ID:
            return self.request_device_id2()
        response = self.session.get(API_GET_BROWSER_DEVICE_ID)
        if response.status_code == 200:
            try:
                result = json.loads(response.text)
                response = self.session.get(b64decode(result['id']).decode())
                if response.text.find('callbackFunction') >= 0:
                    result = response.text[18:-2]
                result = json.loads(result)
                if not Config().is_cache_rail_id_enabled():
                    self.session.cookies.update({
                        'RAIL_EXPIRATION': result.get('exp'),
                        'RAIL_DEVICEID': result.get('dfp'),
                    })
                else:
                    self.session.cookies.update({
                        'RAIL_EXPIRATION': Config().RAIL_EXPIRATION,
                        'RAIL_DEVICEID': Config().RAIL_DEVICEID,
                    })
            except:
                return self.request_device_id()
        else:
            return self.request_device_id()

    def request_device_id2(self):
        headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.61 Safari/537.36"
        }
        self.session.headers.update(headers)
        response = self.session.get(API_GET_BROWSER_DEVICE_ID)
        if response.status_code == 200:
            try:
                if response.text.find('callbackFunction') >= 0:
                    result = response.text[18:-2]
                    result = json.loads(result)
                    if not Config().is_cache_rail_id_enabled():
                       self.session.cookies.update({
                           'RAIL_EXPIRATION': result.get('exp'),
                           'RAIL_DEVICEID': result.get('dfp'),
                       })
                    else:
                       self.session.cookies.update({
                           'RAIL_EXPIRATION': Config().RAIL_EXPIRATION,
                           'RAIL_DEVICEID': Config().RAIL_DEVICEID,
                       })
            except:
                return self.request_device_id2()
        else:
            return self.request_device_id2()

    @classmethod
    def wait_for_ready(cls):
        self = cls()
        if self.is_ready: return self
        stay_second(self.retry_time)
        return self.wait_for_ready()

    @classmethod
    def job_by_name(cls, name) -> Job:
        self = cls()
        for job in self.jobs:
            if job.job_name == name: return job
        return None

    @classmethod
    def job_by_name(cls, name) -> Job:
        self = cls()
        return objects_find_object_by_key_value(self.jobs, 'job_name', name)

    @classmethod
    def job_by_account_key(cls, account_key) -> Job:
        self = cls()
        return objects_find_object_by_key_value(self.jobs, 'account_key', account_key)

    @classmethod
    def get_query_api_type(cls):
        import re
        self = cls()
        if self.api_type:
            return self.api_type
        response = self.session.get(API_QUERY_INIT_PAGE)
        if response.status_code == 200:
            res = re.search(r'var CLeftTicketUrl = \'(.*)\';', response.text)
            try:
                self.api_type = res.group(1)
            except Exception:
                pass
        if not self.api_type:
            QueryLog.add_quick_log('查询地址获取失败, 正在重新获取...').flush()
            sleep(get_interval_num(self.interval))
        self.request_device_id(True)
        return cls.get_query_api_type()

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
