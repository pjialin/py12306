# -*- coding: utf-8 -*-
import json
import logging
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
    log = None

    def __init__(self):
        self.session = Flask(__name__)
        self.log = logging.getLogger('werkzeug')
        self.log.setLevel(logging.ERROR)

        self.register_blueprint()
        self.session.config['JWT_SECRET_KEY'] = 'secret'  # 目前都是本地，暂不用放配置文件
        self.session.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=60 * 60 * 24 * 7)  # Token 超时时间 7 天
        self.jwt = JWTManager(self.session)

    def register_blueprint(self):
        from py12306.web.handler.user import user
        from py12306.web.handler.stat import stat
        from py12306.web.handler.app import app
        from py12306.web.handler.query import query
        from py12306.web.handler.log import log
        self.session.register_blueprint(user)
        self.session.register_blueprint(stat)
        self.session.register_blueprint(app)
        self.session.register_blueprint(query)
        self.session.register_blueprint(log)

    @classmethod
    def run(cls):
        self = cls()
        self.start()

    def start(self):
        if not Config().WEB_ENABLE or Config().is_slave(): return
        # if Config().IS_DEBUG:
        #     self.run_session()
        # else:
        create_thread_and_run(self, 'run_session', wait=False)

    def run_session(self):
        debug = False
        if is_main_thread():
            debug = Config().IS_DEBUG
        self.session.run(debug=debug, port=Config().WEB_PORT, host='0.0.0.0')


if __name__ == '__main__':
    Web.run()
