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

    MESSAGE_SUBSCRIBE_NOTIFICATION_PREFIX = '{} ）'
    MESSAGE_SUBSCRIBE_NOTIFICATION = MESSAGE_SUBSCRIBE_NOTIFICATION_PREFIX + '{}'

    MESSAGE_ASCENDING_MASTER_NODE = '# 已将 {} 提升为主节点，当前节点列表 {} #'

    MESSAGE_MASTER_DID_LOST = '# 主节点已退出，{} 秒后程序将自动退出 #'

    MESSAGE_MASTER_NODE_ALREADY_RUN = '# 启动失败，主节点 {} 已经在运行中 #'
    MESSAGE_MASTER_NODE_NOT_FOUND = '# 启动失败，请先启动主节点 #'

    MESSAGE_NODE_BECOME_MASTER_AGAIN = '# 节点 {} 已启动，已自动成为主节点 #'



    @staticmethod
    def get_print_nodes(nodes):
        message = ['{}{}'.format('*' if val == '1' else '', key) for key, val in nodes.items()]
        return '[ {} ]'.format(', '.join(message))
