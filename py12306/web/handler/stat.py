from flask import Blueprint, request
from flask.json import jsonify
from flask_jwt_extended import (jwt_required)

from py12306.config import Config
from py12306.query.query import Query
from py12306.user.user import User

stat = Blueprint('stat', __name__)


@stat.route('/stat/dashboard', methods=['GET'])
@jwt_required
def dashboard():
    """
    状态统计
    任务数量，用户数量，查询次数
    节点信息（TODO）
    :return:
    """
    from py12306.log.query_log import QueryLog
    query_job_count = len(Query().jobs)
    user_job_count = len(User().users)
    query_count = QueryLog().data.get('query_count')
    res = {
        'query_job_count': query_job_count,
        'user_job_count': user_job_count,
        'query_count': query_count,
    }
    if Config().CDN_ENABLED:
        from py12306.helpers.cdn import Cdn
        res['cdn_count'] = len(Cdn().available_items)
    return jsonify(res)


@stat.route('/stat/cluster', methods=['GET'])
@jwt_required
def clusters():
    """
    节点统计
    节点数量，主节点，子节点列表
    :return:
    """
    from py12306.cluster.cluster import Cluster
    nodes = Cluster().nodes
    count = len(nodes)
    node_lists = list(nodes)
    master = [key for key, val in nodes.items() if int(val) == Cluster.KEY_MASTER]
    master = master[0] if master else ''

    return jsonify({
        'master': master,
        'count': count,
        'node_lists': ', '.join(node_lists)
    })
