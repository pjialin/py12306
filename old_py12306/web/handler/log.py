import linecache

from flask import Blueprint, request
from flask.json import jsonify
from flask_jwt_extended import (jwt_required)

from py12306.config import Config
from py12306.helpers.func import get_file_total_line_num, pick_file_lines
from py12306.log.common_log import CommonLog
from py12306.query.query import Query
from py12306.user.user import User

log = Blueprint('log', __name__)


@log.route('/log/output', methods=['GET'])
@jwt_required
def log_output():
    """
    日志
    :return:
    """
    last_line = int(request.args.get('line', 0))
    limit = int(request.args.get('limit', 10))
    max_old = 200  # 取最新时 往后再取的数
    file = Config().OUT_PUT_LOG_TO_FILE_PATH
    res = []

    if last_line == -1:
        total_line = get_file_total_line_num(file)
        last_line = total_line - max_old if total_line > max_old else 0
        ranges = range(last_line, last_line + max_old + limit)
        # limit = max_old + limit
    else:
        ranges = range(last_line, last_line + limit)

    if Config().OUT_PUT_LOG_TO_FILE_ENABLED:
        with open(Config().OUT_PUT_LOG_TO_FILE_PATH, 'r', encoding='utf-8') as f:
            res = pick_file_lines(f, ranges)

        # linecache.updatecache(file) # 使用 linecache windows 平台会出来编码问题 暂时弃用
        # for i in ranges:
        #     tmp = linecache.getline(file, last_line + i)
        #     if tmp != '': res.append(tmp)
        last_line += len(res)
    else:
        res = CommonLog.MESSAGE_OUTPUT_TO_FILE_IS_UN_ENABLE
    return jsonify({
        'last_line': last_line,
        'data': res
    })
