from py12306.helpers.func import *


class BaseLog:
    logs = []

    @classmethod
    def add_log(cls, content):
        self = cls()
        self.logs.append(content)
        return self

    @classmethod
    def flush(cls):
        self = cls()
        for i in self.logs:
            print(i)
        # print(self.logs)
