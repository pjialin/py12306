import json

from flask import Flask, request
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity)

from py12306.web.handler.user import user

app = Flask(__name__)
app.register_blueprint(user)

# app.config['JWT_TOKEN_LOCATION'] = ['json']
app.config['JWT_SECRET_KEY'] = 'super-secret'  # Change this!
jwt = JWTManager(app)


@app.route('/', methods=['GET'])
def test():
    print(111111)

def run(port=8080):
    app.run(debug=True, port=port if port else 8080, host='0.0.0.0')


if __name__ == '__main__':
    run()
