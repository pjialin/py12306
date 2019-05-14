from flask import Blueprint, request
from flask.json import jsonify
from flask_jwt_extended import (jwt_required, create_access_token)

from py12306.config import Config
from py12306.helpers.func import str_to_time, timestamp_to_time
from py12306.user.job import UserJob
from py12306.user.user import User

user = Blueprint('user', __name__)


@user.route('/login', methods=['POST'])
def login():
    """
    用户登录
    :return:
    """
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    if username and password and username == Config().WEB_USER.get('username') and password == Config().WEB_USER.get(
            'password'):
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token)
    return jsonify({"msg": "用户名或密码错误"}), 422


@user.route('/users', methods=['GET'])
@jwt_required
def users():
    """
    用户任务列表
    :return:
    """
    jobs = User().users
    result = list(map(convert_job_to_info, jobs))
    return jsonify(result)


@user.route('/user/info', methods=['GET'])
@jwt_required
def user_info():
    """
    获取用户信息
    :return:
    """
    result = {
        'name': Config().WEB_USER.get('username')
    }
    return jsonify(result)


def convert_job_to_info(job: UserJob):
    return {
        'key': job.key,
        'user_name': job.user_name,
        'name': job.get_name(),
        'is_ready': job.is_ready,
        'is_loaded': job.user_loaded,  # 是否成功加载 ready 是当前是否可用
        'last_heartbeat': timestamp_to_time(job.last_heartbeat) if job.last_heartbeat else '-',
        'login_num': job.login_num
    }
