import asyncio
import json
import pickle
import random
from json import JSONDecoder
from types import SimpleNamespace
from typing import Any, Optional
from urllib.parse import urlencode, urlparse
from concurrent.futures._base import TimeoutError

import aiohttp
from aiohttp import TraceRequestStartParams, ClientSession, ClientResponse, ClientProxyConnectionError
from app.models import QueryJob
from lib.exceptions import RetryException
from lib.helper import ShareInstance, SuperDict, run_async


class ProxyHelepr(ShareInstance):

    def __init__(self, config: Optional[dict] = None) -> None:
        super().__init__()
        from app.app import Config
        self._config: dict = config or Config.get('proxy')

    async def get_proxy(self):
        if self._config.get('enable') is not True or not self._config.get('url'):
            return None
        response = await Session.share().get(self._config['url'])
        result = response.json()
        if result.get('http'):
            return result.get('http')
        return None


class Session(ShareInstance):

    def __init__(self, use_proxy: bool = False, timeout: int = 0):
        trace_config = aiohttp.TraceConfig()
        trace_config.on_request_start.append(self.on_request_start)
        trace_config.on_request_end.append(self.on_request_end)
        params = {}
        if timeout:
            params['timeout'] = aiohttp.ClientTimeout(total=timeout)
        self.session = aiohttp.ClientSession(trace_configs=[trace_config], **params)
        self.use_proxy = use_proxy
        self.api_base = ''

    @classmethod
    def share_session(cls):
        self = cls.share()
        return self.session

    async def on_request_start(self, session: ClientSession, trace_config_ctx: SimpleNamespace,
                               params: TraceRequestStartParams):
        pass  # TODO

    async def on_request_end(self, session: ClientSession, trace_config_ctx: SimpleNamespace,
                             params: TraceRequestStartParams):
        pass  # TODO

    async def overwrite_text(self, response, *args, **kwargs) -> Any:
        ret = await ClientResponse.text(response, *args, **kwargs)

        def wrap():
            return ret

        return wrap

    def overwrite_json(self, response: ClientResponse) -> Any:
        def wrap(loads: JSONDecoder = json.loads):
            if hasattr(response, 'text_json'):
                return response.text_json
            try:
                load_dict = loads(response.text())
            except Exception:
                load_dict = {}
            ret = SuperDict.dict_to_dict(load_dict)
            response.text_json = ret
            return ret

        return wrap

    def cookie_dumps(self) -> str:
        return pickle.dumps(self.session.cookie_jar._cookies, False).decode()

    def cookie_loads(self, cookies: str):
        self.session.cookie_jar._cookies = pickle.loads(cookies.encode())

    def cookie_clean(self):
        self.session.cookie_jar.clear()

    async def request(self, method: Any, url: str, headers=None, data: Any = None, use_proxy: bool = None,
                      **kwargs: Any) -> ClientResponse:
        from app.app import Logger, Config
        proxy = kwargs.get('proxy', None)
        if proxy is None and (use_proxy is True or (use_proxy is None and self.use_proxy)):
            if random.randint(1, 100) <= Config.get('proxy.rate', 100):
                kwargs['proxy'] = await ProxyHelepr.share().get_proxy()
        # if kwargs.get('proxy'):  # TODO move to event
        #     Logger.debug(f"使用代理 {kwargs['proxy']}")
        default_headers = {
            'User-Agent': f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) '
                          f'Chrome/78.0.{random.randint(3900, 3999)}.97 Safari/537.36'
        }
        if headers:
            default_headers.update(headers)
        parsed_url = urlparse(url)
        if not parsed_url.scheme:
            url = f'{self.api_base}{url}'
        try:
            response = await self.session.request(method, url, headers=default_headers, data=data, **kwargs)
        except Exception as e:
            err = f'{e.__class__.__qualname__} {method} {url}'
            if isinstance(e, TimeoutError):
                err = '请求超时 '
            if isinstance(e, ClientProxyConnectionError):
                err = f"代理连接失败 {kwargs.get('proxy')}"
            Logger.error(f'请求错误, {err}')
            raise RetryException(e, wait_s=1)
        response.text = await self.overwrite_text(response)
        response.json = self.overwrite_json(response)
        return response

    async def get(self, url: str, headers=None, use_proxy: bool = None, **kwargs: Any) -> ClientResponse:
        return await self.request('GET', url=url, headers=headers, use_proxy=use_proxy, **kwargs)

    async def post(self, url: str, headers=None, data: Any = None, use_proxy: bool = None,
                   **kwargs: Any) -> ClientResponse:
        return await self.request('POST', url=url, headers=headers, data=data, use_proxy=use_proxy, **kwargs)

    async def identify_captcha(self, captcha_image64: str):
        data = {
            'img': captcha_image64
        }
        # TODO timeout
        return await self.request('POST', f'https://12306-ocr.pjialin.com/check/', data=data)

    async def browser_device_id_url(self):
        return await self.request('GET', f'https://12306-rail-id-v2.pjialin.com/')

    def __del__(self):
        from app.app import Config
        if Config.IS_IN_TEST:
            run_async(self.session.close())
        else:
            asyncio.ensure_future(self.session.close())


class TrainSession(Session):
    """ 请求处理类 """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_base = 'https://kyfw.12306.cn'

    async def otn_left_ticket_init(self):
        return await self.request('GET', '/otn/leftTicket/init', use_proxy=False)

    async def otn_query_left_ticket(self, api_type: str, queryjob: QueryJob):
        query = {'leftTicketDTO.train_date': queryjob.left_date, 'leftTicketDTO.from_station': queryjob.left_station_id,
                 'leftTicketDTO.to_station': queryjob.arrive_station_id, 'purpose_codes': 'ADULT'}
        url = f'/otn/{api_type}?{urlencode(query)}'
        return await self.request('GET', url, allow_redirects=False)

    async def passport_captcha_image64(self):
        rand_str = random.random()
        return await self.request('GET',
                                  f'/passport/captcha/captcha-image64?login_site=E&module=login&rand=sjrand&_={rand_str}')

    async def passport_captcha_check(self, answer: str):
        """ 验证码校验 """
        rand_str = random.random()
        return await self.request('GET',
                                  f'/passport/captcha/captcha-check?answer={answer}&rand=sjrand&login_site=E&_={rand_str}')

    async def browser_device_id(self, url: str):
        """ 获取浏览器特征 ID """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36'
        }
        return await self.request('GET', url, headers=headers)

    async def passport_web_login(self, data: dict):
        """ 登录 """
        return await self.request('POST', '/passport/web/login', data=data)

    async def passport_web_auth_uamtk(self):
        """ 登录获取 uamtk """
        data = {'appid': 'otn'}
        headers = {
            'Referer': 'https://kyfw.12306.cn/otn/passport?redirect=/otn/login/userLogin',
            'Origin': 'https://kyfw.12306.cn'
        }
        return await self.request('POST', '/passport/web/auth/uamtk', data=data, headers=headers)

    async def otn_uamauthclient(self, uamtk: str):
        """ 登录获取 username  """
        data = {'tk': uamtk}
        return await self.request('POST', '/otn/uamauthclient', data=data)

    async def otn_modify_user_init_query_user_info(self):
        """ 获取用户详情信息 """
        return await self.request('GET', '/otn/modifyUser/initQueryUserInfoApi')

    async def otn_confirm_passenger_get_passenger(self):
        """ 获取乘客列表 """
        return await self.request('POST', '/otn/confirmPassenger/getPassengerDTOs')

    async def otn_login_conf(self):
        """ 获取登录状态 """
        return await self.request('GET', '/otn/login/conf')

    async def otn_left_ticket_submit_order_request(self, data: dict):
        """ 提交下单请求 """
        return await self.request('POST', '/otn/leftTicket/submitOrderRequest', data=data)

    async def otn_confirm_passenger_init_dc(self):
        """ 获取下单 token """
        data = {'_json_att': ''}
        return await self.request('POST', '/otn/confirmPassenger/initDc', data=data)

    async def otn_confirm_passenger_check_order_info(self, data: dict):
        """ 检查下单信息 """
        return await self.request('POST', '/otn/confirmPassenger/checkOrderInfo', data=data)

    async def otn_confirm_passenger_get_queue_count(self, data: dict):
        """ 检查下单信息 """
        return await self.request('POST', '/otn/confirmPassenger/getQueueCount', data=data)

    async def otn_confirm_passenger_confirm_single_for_queue(self, data: dict):
        """ 确认排队 """
        return await self.request('POST', '/otn/confirmPassenger/confirmSingleForQueue', data=data)

    async def otn_confirm_passenger_query_order_wait_time(self, querys: dict):
        """ 查询排队结果 """
        return await self.request('GET', f'/otn/confirmPassenger/queryOrderWaitTime?{urlencode(querys)}')

    async def otn_query_my_order_no_complete(self):
        """ 查询未完成订单 """
        return await self.request('POST', f'/otn/queryOrder/queryMyOrderNoComplete', data={'_json_att': ''})
