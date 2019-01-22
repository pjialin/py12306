import json
import os
import pickle
import sys
import time

import redis
from redis.client import PubSub

from py12306.cluster.redis import Redis
from py12306.config import Config
from py12306.helpers.func import *
from py12306.log.cluster_log import ClusterLog


@singleton
class Cluster():
    KEY_PREFIX = 'py12306_'  # 目前只能手动
    KEY_QUERY_COUNT = KEY_PREFIX + 'query_count'
    KEY_QUERY_LAST_TIME = KEY_PREFIX + 'query_last_time'
    KEY_CONFIGS = KEY_PREFIX + 'configs'
    KEY_NODES = KEY_PREFIX + 'nodes'
    KEY_CHANNEL_LOG = KEY_PREFIX + 'channel_log'
    KEY_CHANNEL_EVENT = KEY_PREFIX + 'channel_even'
    KEY_USER_COOKIES = KEY_PREFIX + 'user_cookies'
    KEY_USER_INFOS = KEY_PREFIX + 'user_infos'
    KEY_USER_LAST_HEARTBEAT = KEY_PREFIX + 'user_last_heartbeat'
    KEY_NODES_ALIVE_PREFIX = KEY_PREFIX + 'nodes_alive_'

    KEY_CDN_AVAILABLE_ITEMS = KEY_PREFIX + 'cdn_available_items'
    KEY_CDN_LAST_CHECK_AT = KEY_PREFIX + 'cdn_last_check_at'

    # 锁
    KEY_LOCK_INIT_USER = KEY_PREFIX + 'lock_init_user'  # 暂未使用
    KEY_LOCK_DO_ORDER = KEY_PREFIX + 'lock_do_order'  # 订单锁
    lock_do_order_time = 60 * 1  # 订单锁超时时间

    lock_prefix = KEY_PREFIX + 'lock_'  # 锁键前缀
    lock_info_prefix = KEY_PREFIX + 'info_'

    KEY_MASTER = 1
    KEY_SLAVE = 0

    session: Redis = None
    pubsub: PubSub = None
    refresh_channel_time = 0.5
    retry_time = 2
    keep_alive_time = 3  # 报告存活间隔
    lost_alive_time = keep_alive_time * 2

    nodes = {}
    node_name = None
    is_ready = False
    is_master = False

    def __init__(self, *args):
        if Config.is_cluster_enabled():
            self.session = Redis()
        return self

    @classmethod
    def run(cls):
        self = cls()
        self.start()

    def start(self):
        self.pubsub = self.session.pubsub()
        self.pubsub.subscribe(self.KEY_CHANNEL_LOG, self.KEY_CHANNEL_EVENT)
        create_thread_and_run(self, 'subscribe', wait=False)
        self.is_ready = True
        self.get_nodes()  # 提前获取节点列表
        self.check_nodes()  # 防止 节点列表未清空
        self.join_cluster()
        create_thread_and_run(self, 'keep_alive', wait=False)
        create_thread_and_run(self, 'refresh_data', wait=False)

    def join_cluster(self):
        """
        加入到集群
        :return:
        """
        self.node_name = node_name = Config().NODE_NAME

        if Config().NODE_IS_MASTER:
            if self.node_name in self.nodes:  # 重复运行主节点
                ClusterLog.add_quick_log(ClusterLog.MESSAGE_MASTER_NODE_ALREADY_RUN.format(node_name)).flush(
                    publish=False)
                os._exit(1)
            if self.have_master():  # 子节点提升为主节点情况，交回控制
                message = ClusterLog.MESSAGE_NODE_BECOME_MASTER_AGAIN.format(node_name)
                self.publish_log_message(message)
                self.make_nodes_as_slave()
        elif not self.have_master():  # 只能通过主节点启动
            ClusterLog.add_quick_log(ClusterLog.MESSAGE_MASTER_NODE_NOT_FOUND).flush(publish=False)
            os._exit(1)

        if node_name in self.nodes:
            self.node_name = node_name = node_name + '_' + str(dict_count_key_num(self.nodes, node_name))
            ClusterLog.add_quick_log(ClusterLog.MESSAGE_NODE_ALREADY_IN_CLUSTER.format(node_name)).flush()

        self.session.hset(self.KEY_NODES, node_name, Config().NODE_IS_MASTER)
        message = ClusterLog.MESSAGE_JOIN_CLUSTER_SUCCESS.format(self.node_name, ClusterLog.get_print_nodes(
            self.get_nodes()))  # 手动 get nodes
        self.publish_log_message(message)

    def left_cluster(self, node_name=None):
        node_name = node_name if node_name else self.node_name
        self.session.hdel(self.KEY_NODES, node_name)
        message = ClusterLog.MESSAGE_LEFT_CLUSTER.format(node_name, ClusterLog.get_print_nodes(self.get_nodes()))
        self.publish_log_message(message, node_name)

    def make_nodes_as_slave(self):
        """
        将所有节点设为主节点
        :return:
        """
        for node in self.nodes:
            self.session.hset(self.KEY_NODES, node, self.KEY_SLAVE)

    def publish_log_message(self, message, node_name=None):
        """
        发布订阅消息
        :return:
        """
        node_name = node_name if node_name else self.node_name
        message = ClusterLog.MESSAGE_SUBSCRIBE_NOTIFICATION.format(node_name, message)
        self.session.publish(self.KEY_CHANNEL_LOG, message)

    def publish_event(self, name, data={}):
        """
        发布事件消息
        :return:
        """
        data = {'event': name, 'data': data}
        self.session.publish(self.KEY_CHANNEL_EVENT, json.dumps(data))

    def get_nodes(self) -> dict:
        res = self.session.hgetall(self.KEY_NODES)
        res = res if res else {}
        self.nodes = res
        return res

    def refresh_data(self):
        """
        单独进程处理数据同步
        :return:
        """
        while True:
            self.get_nodes()
            self.check_locks()
            self.check_nodes()
            self.check_master()
            stay_second(self.retry_time)

    def check_master(self):
        """
        检测主节点是否可用
        :return:
        """
        master = self.have_master()
        if master == self.node_name:  # 动态提升
            self.is_master = True
        else:
            self.is_master = False

        if not master:
            if Config().NODE_SLAVE_CAN_BE_MASTER:
                # 提升子节点为主节点
                slave = list(self.nodes)[0]
                self.session.hset(self.KEY_NODES, slave, self.KEY_MASTER)
                self.publish_log_message(ClusterLog.MESSAGE_ASCENDING_MASTER_NODE.format(slave,
                                                                                         ClusterLog.get_print_nodes(
                                                                                             self.get_nodes())))
                return True
            else:
                self.publish_log_message(ClusterLog.MESSAGE_MASTER_DID_LOST.format(self.retry_time))
                stay_second(self.retry_time)
                os._exit(1)  # 退出整个程序

    def have_master(self):
        return dict_find_key_by_value(self.nodes, str(self.KEY_MASTER), False)

    def check_nodes(self):
        """
        检查节点是否存活
        :return:
        """
        for node in self.nodes:
            if not self.session.exists(self.KEY_NODES_ALIVE_PREFIX + node):
                self.left_cluster(node)

    # def kick_out_from_nodes(self, node_name):
    #     pass

    def keep_alive(self):
        while True:
            if self.node_name not in self.get_nodes():  # 已经被 kict out  重新加下
                self.join_cluster()
            self.session.set(self.KEY_NODES_ALIVE_PREFIX + self.node_name, Config().NODE_IS_MASTER, ex=self.lost_alive_time)
            stay_second(self.keep_alive_time)

    def subscribe(self):
        while True:
            try:
                message = self.pubsub.get_message()
            except RuntimeError as err:
                if 'args' in dir(err) and err.args[0].find('pubsub connection not set') >= 0:  # 失去重连
                    self.pubsub.subscribe(self.KEY_CHANNEL_LOG, self.KEY_CHANNEL_EVENT)
                    continue
            if message:
                if message.get('type') == 'message' and message.get('channel') == self.KEY_CHANNEL_LOG and message.get(
                        'data'):
                    msg = message.get('data')
                    if self.node_name:
                        msg = msg.replace(ClusterLog.MESSAGE_SUBSCRIBE_NOTIFICATION_PREFIX.format(self.node_name), '')
                    ClusterLog.add_quick_log(msg).flush(publish=False)
                elif message.get('channel') == self.KEY_CHANNEL_EVENT:
                    create_thread_and_run(self, 'handle_events', args=(message,))
            stay_second(self.refresh_channel_time)

    def handle_events(self, message):
        # 这里应该分开处理，先都在这处理了
        if message.get('type') != 'message': return
        result = json.loads(message.get('data', {}))
        event_name = result.get('event')
        data = result.get('data')
        from py12306.helpers.event import Event
        method = getattr(Event(), event_name)
        if method:
            create_thread_and_run(Event(), event_name, Const.IS_TEST, kwargs={'data': data, 'callback': True})

    def get_lock(self, key: str, timeout=1, info={}):
        timeout = int(time.time()) + timeout
        res = self.session.setnx(key, timeout)
        if res:
            if info: self.session.set_dict(self.lock_info_prefix + key.replace(self.KEY_PREFIX, ''), info)  # 存储额外信息
            return True
        return False

    def get_lock_info(self, key, default={}):
        return self.session.get_dict(self.lock_info_prefix + key.replace(self.KEY_PREFIX, ''), default=default)

    def release_lock(self, key):
        self.session.delete(key)
        self.session.delete(self.lock_info_prefix + key.replace(self.KEY_PREFIX, ''))

    def check_locks(self):
        locks = self.session.keys(self.lock_prefix + '*')
        for key in locks:
            val = self.session.get(key)
            if val and int(val) <= time_int():
                self.release_lock(key)

    @classmethod
    def get_user_cookie(cls, key, default=None):
        self = cls()
        res = self.session.hget(Cluster.KEY_USER_COOKIES, key)
        return pickle.loads(res.encode()) if res else default

    @classmethod
    def set_user_cookie(cls, key, value):
        self = cls()
        return self.session.hset(Cluster.KEY_USER_COOKIES, key, pickle.dumps(value, 0).decode())

    @classmethod
    def set_user_info(cls, key, info):
        self = cls()
        return self.session.hset(Cluster.KEY_USER_INFOS, key, pickle.dumps(info, 0).decode())

    @classmethod
    def get_user_info(cls, key, default=None):
        self = cls()
        res = self.session.hget(Cluster.KEY_USER_INFOS, key)
        return pickle.loads(res.encode()) if res else default
