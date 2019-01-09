from py12306.log.base import BaseLog
from py12306.helpers.func import *


@singleton
class ClusterLog(BaseLog):
    # 这里如果不声明，会出现重复打印，目前不知道什么原因
    logs = []
    thread_logs = {}
    quick_log = []

    MESSAGE_JOIN_CLUSTER_SUCCESS = '# 节点 {} 成功加入到集群，当前节点列表 {} #'
    MESSAGE_LEFT_CLUSTER = '# 节点 {} 已离开集群，当前节点列表 {} #'

    MESSAGE_NODE_ALREADY_IN_CLUSTER = '# 当前节点已存在于集群中，自动分配新的节点名称 {} #'
