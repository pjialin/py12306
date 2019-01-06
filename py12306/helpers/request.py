from requests_html import HTMLSession


class Request(HTMLSession):
    """
    请求处理类
    """
    # session = {}

    # def __init__(self, mock_browser=True, session=None):
    # super().__init__(mock_browser=mock_browser)
    # self.session = session if session else HTMLSession()
    pass

    def save_to_file(self, url, path):
        response = self.get(url, stream=True)
        with open(path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                f.write(chunk)
        return response
