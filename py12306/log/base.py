from py12306.helpers.func import *


class BaseLog:
    logs = []
    quick_log = []

    @classmethod
    def add_log(cls, content):
        self = cls()
        self.logs.append(content)
        return self

    @classmethod
    def flush(cls, sep='\n', end='\n', file=None):
        self = cls()
        logs = self.quick_log if self.quick_log else self.logs
        # for i in logs:
        print(*logs, sep=sep, end=end, file=file)
        if self.quick_log:
            self.quick_log = []
        else:
            self.logs = []
        # print(self.logs)

    @classmethod
    def add_quick_log(cls, content):
        self = cls()
        self.quick_log.append(content)
        return self
