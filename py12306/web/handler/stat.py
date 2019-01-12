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
    return jsonify({
        'query_job_count': query_job_count,
        'user_job_count': user_job_count,
        'query_count': query_count
    })
