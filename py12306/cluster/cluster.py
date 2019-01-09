import redis
from redis.client import PubSub

from py12306.cluster.redis import Redis
from py12306.config import Config
from py12306.helpers.func import *
from py12306.log.cluster_log import ClusterLog


@singleton
class Distributed():
    KEY_QUERY_COUNT = 'query_count'
    KEY_QUERY_LAST_TIME = 'query_last_time'
    KEY_CONFIGS = 'configs'
    KEY_NODES = 'nodes'
    KEY_CHANNEL_LOG = 'channel_log'

    session: Redis = None
    pubsub: PubSub = None
    refresh_channel_time = 0.5
    retry_time = 2

    nodes = {}

    def __init__(self, *args):
        self.session = Redis()
        self.pubsub = self.session.pubsub()
        self.pubsub.subscribe(self.KEY_CHANNEL_LOG)
        create_thread_and_run(self, 'refresh_data', wait=False)
        create_thread_and_run(self, 'subscribe', wait=False)
        return self

    def join_cluster(self):
        node_name = Config().NODE_NAME
        if node_name in self.nodes:
            node_name = node_name + '_' + str(dict_count_key_num(self.nodes, node_name))
            ClusterLog.add_quick_log(ClusterLog.MESSAGE_NODE_ALREADY_IN_CLUSTER.format(node_name)).flush()

        self.session.hset(self.KEY_NODES, node_name, Config().NODE_IS_MASTER)
        message = ClusterLog.MESSAGE_JOIN_CLUSTER_SUCCESS.format(Config().NODE_NAME, list(self.get_nodes()))
        # ClusterLog.add_quick_log(message).flush()
        self.session.publish(self.KEY_CHANNEL_LOG, message)

    def left_cluster(self):
        self.session.hdel(self.KEY_NODES, Config().NODE_NAME)
        message = ClusterLog.MESSAGE_LEFT_CLUSTER.format(Config().NODE_NAME, list(self.get_nodes()))
        # ClusterLog.add_quick_log(message).flush()
        self.session.publish(self.KEY_CHANNEL_LOG, message)

    def get_nodes(self):
        res = self.session.hgetall(self.KEY_NODES)
        res = res if res else {}
        self.nodes = res
        return res

    def refresh_data(self):
        while True:
            self.get_nodes()
            stay_second(self.retry_time)

    def subscribe(self):
        while True:
            message = self.pubsub.get_message()
            if message:
                if message.get('type') == 'message' and message.get('data'):
                    ClusterLog.add_quick_log(message.get('data')).flush()
            stay_second(self.refresh_channel_time)
