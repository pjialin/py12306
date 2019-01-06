# encoding=utf8
import os
from threading import Thread

from py12306.log.query_log import QueryLog
from py12306.query.query import Query
from py12306.user.user import User


def main():
    # Thread(target=Query.run).start()  # 余票查询
    # QueryLog.add_log('init')
    # Query.run()
    User.run()
    pass


if __name__ == '__main__':
    main()
