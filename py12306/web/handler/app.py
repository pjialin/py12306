from flask import Blueprint, request
from flask.json import jsonify
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity)

from py12306.config import Config
from py12306.query.query import Query
from py12306.user.user import User

app = Blueprint('app', __name__)


@app.route('/app/menus', methods=['GET'])
@jwt_required
def menus():
    """
    菜单列表
    """
    menus = [
        {"id": 10, "name": "首页", "url": "/", "icon": "fa fa-tachometer-alt"},
        {"id": 40, "name": "数据分析", "url": "/analyze", "icon": "fa fa-signature"},
        {"id": 50, "name": "帮助中心", "url": "/help", "icon": "fa fa-search"}
    ]
    return jsonify(menus)


@app.route('/app/actions', methods=['GET'])
@jwt_required
def actions():
    """
    操作列表
    """
    actions = [
        {"text": "退出登录", "link": "", "icon": "fa fa-sign-out-alt"}
    ]
    return jsonify(actions)
