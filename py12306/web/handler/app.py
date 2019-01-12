import json
import re

from flask import Blueprint, request, send_file
from flask.json import jsonify
from flask_jwt_extended import (jwt_required)

from py12306.config import Config
from py12306.query.query import Query
from py12306.user.user import User

app = Blueprint('app', __name__)


@app.route('/', methods=['GET', 'POST'])
def index():
    file = Config().WEB_ENTER_HTML_PATH
    result = ''
    with open(file, 'r', encoding='utf-8') as f:
        result = f.read()
        config = {
            'API_BASE_URL': ''  # TODO 自定义 Host
        }
        result = re.sub(r'<script>[\s\S]*?<\/script>', '<script>window.config={}</script>'.format(json.dumps(config)),
                        result)

    return result


@app.route('/app/menus', methods=['GET'])
@jwt_required
def menus():
    """
    菜单列表
    """
    menus = [
        {"id": 10, "name": "首页", "url": "/", "icon": "fa fa-tachometer-alt"},
        {"id": 20, "name": "用户管理", "url": "/user", "icon": "fa fa-user"},
        {"id": 30, "name": "查询任务", "url": "/query", "icon": "fa fa-infinity"},
        {"id": 40, "name": "实时日志", "url": "/log/realtime", "icon": "fa fa-signature"},
        {"id": 50, "name": "帮助", "url": "/help", "icon": "fa fa-search"}
    ]
    return jsonify(menus)


@app.route('/app/actions', methods=['GET'])
@jwt_required
def actions():
    """
    操作列表
    """
    actions = [
        {"text": "退出登录", "key": 'logout', "link": "", "icon": "fa fa-sign-out-alt"}
    ]
    return jsonify(actions)
