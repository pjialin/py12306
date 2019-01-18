from flask import Blueprint, request
from flask.json import jsonify
from flask_jwt_extended import (jwt_required)

from py12306.config import Config
from py12306.query.job import Job
from py12306.query.query import Query

query = Blueprint('query', __name__)


@query.route('/query', methods=['GET'])
@jwt_required
def query_lists():
    """
    查询任务列表
    :return:
    """
    jobs = Query().jobs
    result = list(map(convert_job_to_info, jobs))
    return jsonify(result)


def convert_job_to_info(job: Job):
    return {
        'name': job.job_name,
        'left_dates': job.left_dates,
        'stations': job.stations,
        'members': job.members,
        'member_num': job.member_num,
        'allow_seats': job.allow_seats,
        'allow_train_numbers': job.allow_train_numbers,
        'except_train_numbers': job.except_train_numbers,
        'allow_less_member': job.allow_less_member,
        'passengers': job.passengers,
    }
