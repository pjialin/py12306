import json

from flask import Flask, request
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity)

from py12306.helpers.func import *


# app.config['JWT_TOKEN_LOCATION'] = ['json']


# @flask.route('/', methods=['GET'])
# def test():
#     print(111111)


# def run(port=8080):
#     flask.run(debug=True, port=port if port else 8080, host='0.0.0.0')


@singleton
class Web:
    session = None
    jwt = None

    def __init__(self):
        self.session = Flask(__name__)
        self.register_blueprint()
        self.session.config['JWT_SECRET_KEY'] = 'super-secret'  # Change this!
        self.jwt = JWTManager(self.session)
        pass

    def register_blueprint(self):
        from py12306.web.handler.user import user
        from py12306.web.handler.stat import stat
        from py12306.web.handler.app import app
        self.session.register_blueprint(user)
        self.session.register_blueprint(stat)
        self.session.register_blueprint(app)

    @classmethod
    def run(cls):
        self = cls()
        self.start()
        pass

    def start(self):
        self.session.run(debug=True, port=8080, host='0.0.0.0')


if __name__ == '__main__':
    Web.run()
