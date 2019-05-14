from py12306.helpers.func import *
from py12306.config import Config


@singleton
class Event():
    """
    处理事件
    """
    # 事件
    KEY_JOB_DESTROY = 'job_destroy'
    KEY_USER_JOB_DESTROY = 'user_job_destroy'
    KEY_USER_LOADED = 'user_loaded'
    cluster = None

    def __init__(self):
        from py12306.cluster.cluster import Cluster
        self.cluster = Cluster()

    def job_destroy(self, data={}, callback=False):  # 停止查询任务
        from py12306.query.query import Query
        if Config().is_cluster_enabled() and not callback:
            return self.cluster.publish_event(self.KEY_JOB_DESTROY, data)  # 通知其它节点退出

        job = Query.job_by_name(data.get('name'))
        if job:
            job.destroy()

    def user_loaded(self, data={}, callback=False):  # 用户初始化完成
        if Config().is_cluster_enabled() and not callback:
            return self.cluster.publish_event(self.KEY_USER_LOADED, data)  # 通知其它节点退出
        from py12306.query.query import Query

        if not Config().is_cluster_enabled() or Config().is_master():
            query = Query.wait_for_ready()
            for job in query.jobs:
                if job.account_key == data.get('key'):
                    create_thread_and_run(job, 'check_passengers', Const.IS_TEST)  # 检查乘客信息 防止提交订单时才检查
                    stay_second(1)

    def user_job_destroy(self, data={}, callback=False):
        from py12306.user.user import User
        if Config().is_cluster_enabled() and not callback:
            return self.cluster.publish_event(self.KEY_JOB_DESTROY, data)  # 通知其它节点退出

        user = User.get_user(data.get('key'))
        if user:
            user.destroy()
