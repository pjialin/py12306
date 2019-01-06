# encoding=utf8
import os
from threading import Thread

from py12306.helpers.func import *
from py12306.query.query import Query
from py12306.user.user import User


def main():
    # Thread(target=Query.run).start()  # 余票查询
    create_thread_and_run(User, 'run', wait=False)
    Query.run()
    # Query.run()
    pass


if __name__ == '__main__':
    main()
