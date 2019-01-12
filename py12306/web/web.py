import json
from datetime import timedelta

from flask import Flask, request
from flask_jwt_extended import (
    JWTManager)

from py12306.config import Config
from py12306.helpers.func import *


@singleton
class Web:
    session = None
    jwt = None

    def __init__(self):
        self.session = Flask(__name__)
        self.register_blueprint()
        self.session.config['JWT_SECRET_KEY'] = 'secret'  # 目前都是本地，暂不用放配置文件
        self.session.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(seconds=60 * 60 * 24 * 7)  # Token 超时时间 7 天
        self.jwt = JWTManager(self.session)
        pass

    def register_blueprint(self):
        from py12306.web.handler.user import user
        from py12306.web.handler.stat import stat
        from py12306.web.handler.app import app
        from py12306.web.handler.query import query
        self.session.register_blueprint(user)
        self.session.register_blueprint(stat)
        self.session.register_blueprint(app)
        self.session.register_blueprint(query)

    @classmethod
    def run(cls):
        self = cls()
        self.start()
        pass

    def start(self):
        self.session.run(debug=Config().IS_DEBUG, port=Config().WEB_PORT, host='0.0.0.0')


if __name__ == '__main__':
    Web.run()
