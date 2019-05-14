import requests
from requests.exceptions import *
from requests_html import HTMLSession, HTMLResponse

from py12306.lib.func import expand_class

requests.packages.urllib3.disable_warnings()


class Request(HTMLSession):
    """
    请求处理类
    """

    def save_to_file(self, url, path):
        response = self.get(url, stream=True)
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
        return response

    @staticmethod
    def _handle_response(response, **kwargs) -> HTMLResponse:
        """
        扩充 response
        :param response:
        :param kwargs:
        :return:
        """
        response = HTMLSession._handle_response(response, **kwargs)
        expand_class(response, 'json', Request.json)
        return response

    def add_response_hook(self, hook):
        hooks = self.hooks['response']
        if not isinstance(hooks, list):
            hooks = [hooks]
        hooks.append(hook)
        self.hooks['response'] = hooks
        return self

    def json(self, default={}):
        """
        重写 json 方法，拦截错误
        :return:
        """
        from py12306.lib.helper import Dict
        try:
            result = self.old_json()
            return Dict(result)
        except:
            return Dict(default)

    def request(self, *args, **kwargs):
        try:
            if 'timeout' not in kwargs:
                from py12306.app.app import Config
                kwargs['timeout'] = Config.REQUEST_TIME_OUT
            response = super().request(*args, **kwargs)
            return response
        except RequestException as e:
            if e.response:
                response = e.response
            else:
                response = HTMLResponse(HTMLSession)
                # response.status_code = 500
                expand_class(response, 'json', Request.json)
            return response
