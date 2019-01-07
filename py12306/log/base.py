import os
import sys

from py12306.helpers.func import *


class BaseLog:
    logs = []
    thread_logs = {}
    quick_log = []

    @classmethod
    def add_log(cls, content):
        self = cls()
        # print('添加 Log 主进程{} 进程ID{}'.format(is_main_thread(), current_thread_id()))
        if is_main_thread():
            self.logs.append(content)
        else:
            tmp_log = self.thread_logs.get(current_thread_id(), [])
            tmp_log.append(content)
            self.thread_logs[current_thread_id()] = tmp_log
        return self

    @classmethod
    def flush(cls, sep='\n', end='\n', file=None):
        self = cls()
        if self.quick_log:
            logs = self.quick_log
        else:
            if is_main_thread():
                logs = self.logs
            else:
                logs = self.thread_logs.get(current_thread_id())
        # for i in logs:
        print(*logs, sep=sep, end=end, file=file)
        if self.quick_log:
            self.quick_log = []
        else:
            if is_main_thread():
                self.logs = []
            else:
                if logs: del self.thread_logs[current_thread_id()]
        # print(self.logs)

    @classmethod
    def add_quick_log(cls, content):
        self = cls()
        self.quick_log.append(content)
        return self

    def notification(self, title, content=''):
        if sys.platform == 'darwin':
            os.system(
                'osascript -e \'tell app "System Events" to display notification "{content}" with title "{title}"\''.format(
                    title=title, content=content))
