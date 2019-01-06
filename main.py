# encoding=utf8

from threading import Thread

from py12306.log.query_log import QueryLog
from py12306.query.query import Query


def main():
    # Thread(target=Query.run).start()  # 余票查询
    QueryLog.add_log('init')
    Query.run()
    pass


if __name__ == '__main__':
    main()
