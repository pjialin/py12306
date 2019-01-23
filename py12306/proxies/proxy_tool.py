# -*- coding: utf-8 -*-

import re
import requests
from lxml import etree
from py12306.proxies.utils.WebRequest import WebRequest
from py12306.helpers.func import *

# for debug to disable insecureWarning
requests.packages.urllib3.disable_warnings()

"""
    66ip.cn
    data5u.com
    xicidaili.com
    goubanjia.com
    xdaili.cn
    kuaidaili.com
    cn-proxy.com
    proxy-list.org
    www.mimiip.com to do
"""


def getHtmlTree(url, **kwargs):
    """
    获取html树
    :param url:
    :param kwargs:
    :return:
    """

    header = {'Connection': 'keep-alive',
              'Cache-Control': 'max-age=0',
              'Upgrade-Insecure-Requests': '1',
              'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko)',
              'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
              'Accept-Encoding': 'gzip, deflate, sdch',
              'Accept-Language': 'zh-CN,zh;q=0.8',
              }
    # TODO 取代理服务器用代理服务器访问
    wr = WebRequest()

    # delay 2s for per request
    time.sleep(2)

    html = wr.get(url=url, header=header).content
    return etree.HTML(html)


class GetFreeProxy(object):
    """
    proxy getter
    """

    @staticmethod
    def freeProxyFirst(page=10):
        """
        无忧代理 http://www.data5u.com/
        几乎没有能用的
        :param page: 页数
        :return:
        """
        url_list = [
            'http://www.data5u.com/',
            'http://www.data5u.com/free/gngn/index.shtml',
            'http://www.data5u.com/free/gnpt/index.shtml'
        ]
        for url in url_list:
            html_tree = getHtmlTree(url)
            ul_list = html_tree.xpath('//ul[@class="l2"]')
            for ul in ul_list:
                try:
                    yield ':'.join(ul.xpath('.//li/text()')[0:2])
                except Exception as e:
                    print(e)

    @staticmethod
    def freeProxySecond(area=33, page=1):
        """
        代理66 http://www.66ip.cn/
        :param area: 抓取代理页数，page=1北京代理页，page=2上海代理页......
        :param page: 翻页
        :return:
        """
        area = 33 if area > 33 else area
        for area_index in range(1, area + 1):
            for i in range(1, page + 1):
                url = "http://www.66ip.cn/areaindex_{}/{}.html".format(area_index, i)
                html_tree = getHtmlTree(url)
                tr_list = html_tree.xpath("//*[@id='footer']/div/table/tr[position()>1]")
                if len(tr_list) == 0:
                    continue
                for tr in tr_list:
                    yield tr.xpath("./td[1]/text()")[0] + ":" + tr.xpath("./td[2]/text()")[0]
                break

    @staticmethod
    def freeProxyThird(days=1):
        """
        ip181 http://www.ip181.com/  不能用了
        :param days:
        :return:
        """
        url = 'http://www.ip181.com/'
        html_tree = getHtmlTree(url)
        try:
            tr_list = html_tree.xpath('//tr')[1:]
            for tr in tr_list:
                yield ':'.join(tr.xpath('./td/text()')[0:2])
        except Exception as e:
            pass

    @staticmethod
    def freeProxyFourth(page_count=2):
        """
        西刺代理 http://www.xicidaili.com
        :return:
        """
        url_list = [
            'http://www.xicidaili.com/nn/',  # 高匿
            'http://www.xicidaili.com/nt/',  # 透明
        ]
        for each_url in url_list:
            for i in range(1, page_count + 1):
                page_url = each_url + str(i)
                tree = getHtmlTree(page_url)
                proxy_list = tree.xpath('.//table[@id="ip_list"]//tr[position()>1]')
                for proxy in proxy_list:
                    try:
                        yield ':'.join(proxy.xpath('./td/text()')[0:2])
                    except Exception as e:
                        pass

    @staticmethod
    def freeProxyFifth():
        """
        guobanjia http://www.goubanjia.com/
        :return:
        """
        url = "http://www.goubanjia.com/"
        tree = getHtmlTree(url)
        proxy_list = tree.xpath('//td[@class="ip"]')
        # 此网站有隐藏的数字干扰，或抓取到多余的数字或.符号
        # 需要过滤掉<p style="display:none;">的内容
        xpath_str = """.//*[not(contains(@style, 'display: none'))
                                        and not(contains(@style, 'display:none'))
                                        and not(contains(@class, 'port'))
                                        ]/text()
                                """
        for each_proxy in proxy_list:
            try:
                # :符号裸放在td下，其他放在div span p中，先分割找出ip，再找port
                ip_addr = ''.join(each_proxy.xpath(xpath_str))
                port = each_proxy.xpath(".//span[contains(@class, 'port')]/text()")[0]
                yield '{}:{}'.format(ip_addr, port)
            except Exception as e:
                pass

    @staticmethod
    def freeProxySixth():
        """
        讯代理 http://www.xdaili.cn/
        :return:
        """
        url = 'http://www.xdaili.cn/ipagent/freeip/getFreeIps?page=1&rows=10'
        request = WebRequest()
        try:
            res = request.get(url, timeout=10).json()
            for row in res['RESULT']['rows']:
                yield '{}:{}'.format(row['ip'], row['port'])
        except Exception as e:
            pass

    @staticmethod
    def freeProxySeventh():
        """
        快代理 https://www.kuaidaili.com
        """
        url_list = [
            'https://www.kuaidaili.com/free/inha/{page}/',
            'https://www.kuaidaili.com/free/intr/{page}/'
        ]
        for url in url_list:
            for page in range(1, 2):
                page_url = url.format(page=page)
                tree = getHtmlTree(page_url)
                proxy_list = tree.xpath('.//table//tr')
                for tr in proxy_list[1:]:
                    yield ':'.join(tr.xpath('./td/text()')[0:2])

    @staticmethod
    def freeProxyEight():
        """
        秘密代理 http://www.mimiip.com
        """
        url_gngao = ['http://www.mimiip.com/gngao/%s' % n for n in range(1, 2)]  # 国内高匿
        url_gnpu = ['http://www.mimiip.com/gnpu/%s' % n for n in range(1, 2)]  # 国内普匿
        url_gntou = ['http://www.mimiip.com/gntou/%s' % n for n in range(1, 2)]  # 国内透明
        url_list = url_gngao + url_gnpu + url_gntou

        request = WebRequest()
        for url in url_list:
            r = request.get(url, timeout=10)
            proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\w\W].*<td>(\d+)</td>', r.text)
            for proxy in proxies:
                yield ':'.join(proxy)

    @staticmethod
    def freeProxyNinth():
        """
        码农代理 https://proxy.coderbusy.com/
        :return:
        """
        urls = ['https://proxy.coderbusy.com/classical/country/cn.aspx?page=1']
        request = WebRequest()
        for url in urls:
            r = request.get(url, timeout=10)
            proxies = re.findall('data-ip="(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})".+?>(\d+)</td>', r.text)
            for proxy in proxies:
                yield ':'.join(proxy)

    @staticmethod
    def freeProxyTen():
        """
        云代理 http://www.ip3366.net/free/
        :return:
        """
        urls = ['http://www.ip3366.net/free/']
        request = WebRequest()
        for url in urls:
            r = request.get(url, timeout=10)
            proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\s\S]*?<td>(\d+)</td>', r.text)
            for proxy in proxies:
                yield ":".join(proxy)

    @staticmethod
    def freeProxyEleven():
        """
        IP海 http://www.iphai.com/free/ng
        :return:
        """
        urls = [
            'http://www.iphai.com/free/ng',
            'http://www.iphai.com/free/np',
            'http://www.iphai.com/free/wg',
            'http://www.iphai.com/free/wp'
        ]
        request = WebRequest()
        for url in urls:
            r = request.get(url, timeout=10)
            proxies = re.findall(r'<td>\s*?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*?</td>[\s\S]*?<td>\s*?(\d+)\s*?</td>',
                                 r.text)
            for proxy in proxies:
                yield ":".join(proxy)

    @staticmethod
    def freeProxyTwelve(page_count=2):
        """
        guobanjia http://ip.jiangxianli.com/?page=
        免费代理库
        超多量
        :return:
        """
        for i in range(1, page_count + 1):
            url = 'http://ip.jiangxianli.com/?page={}'.format(i)
            html_tree = getHtmlTree(url)
            tr_list = html_tree.xpath("/html/body/div[1]/div/div[1]/div[2]/table/tbody/tr")
            if len(tr_list) == 0:
                continue
            for tr in tr_list:
                yield tr.xpath("./td[2]/text()")[0] + ":" + tr.xpath("./td[3]/text()")[0]

    @staticmethod
    def freeProxyWallFirst():
        """
        墙外网站 cn-proxy
        :return:
        """
        urls = ['http://cn-proxy.com/', 'http://cn-proxy.com/archives/218']
        request = WebRequest()
        for url in urls:
            r = request.get(url, timeout=10)
            proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\w\W]<td>(\d+)</td>', r.text)
            for proxy in proxies:
                yield ':'.join(proxy)

    @staticmethod
    def freeProxyWallSecond():
        """
        https://proxy-list.org/english/index.php
        :return:
        """
        urls = ['https://proxy-list.org/english/index.php?p=%s' % n for n in range(1, 10)]
        request = WebRequest()
        import base64
        for url in urls:
            r = request.get(url, timeout=10)
            proxies = re.findall(r"Proxy\('(.*?)'\)", r.text)
            for proxy in proxies:
                yield base64.b64decode(proxy).decode()

    @staticmethod
    def freeProxyWallThird():
        urls = ['https://list.proxylistplus.com/Fresh-HTTP-Proxy-List-1']
        request = WebRequest()
        for url in urls:
            r = request.get(url, timeout=10)
            proxies = re.findall(r'<td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td>[\s\S]*?<td>(\d+)</td>', r.text)
            for proxy in proxies:
                yield ':'.join(proxy)

    def verifyProxyFormat(proxy):
        """
        检查代理格式
        :param proxy:
        :return:
        """
        import re
        verify_regex = r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}"
        _proxy = re.findall(verify_regex, str(proxy))
        return True if len(_proxy) == 1 and _proxy[0] == proxy else False

    @staticmethod
    def validUsefulProxy(proxies, useful_ips=None, flag=None):
        """
        检验代理是否可用
        :param flag:
        :param useful_ips:
        :param proxies:
        :return:
        """
        if isinstance(proxies, bytes):
            proxies = proxies.decode('utf8')
        for proxy in proxies:
            _proxy = {"http": "http://{proxy}".format(proxy=proxy)}
            useful = None
            try:
                # 超过20秒的代理就不要了
                r = requests.get('http://httpbin.org/ip', proxies=_proxy, timeout=2, verify=False)
                if r.status_code == 200 and r.json().get("origin"):
                    print('{} is ok'.format(proxy))
                    # BaseLog.add_quick_log('{} is ok'.format(proxy))
                    useful = True
            except Exception as e:
                useful = False
            if useful:
                useful_ips.append(proxy)
        flag.append(True)

    @staticmethod
    def getAllProxy():
        """
            获取所有免费的代理ip
        :return:
        """
        print('正在更新ip池,请稍后...')
        proxies = GetFreeProxy.get_list_proxies()
        for i in range(len(proxies)):
            if proxies[i] and not GetFreeProxy.verifyProxyFormat(proxies[i]):
                proxies.remove(proxies[i])
        GetFreeProxy.check_ip_available(proxies, thread=10)

    @staticmethod
    def check_ip_available(proxies, thread=10):
        print('正在检查ip可用性...')
        print('总ip数： ', len(proxies))
        ip_list = []

        flag = list()
        start = 0
        threads = 0
        for index in range(0, len(proxies)):
            end = index
            if (end - start) == int(len(proxies) / thread):
                create_thread_and_run(GetFreeProxy, 'validUsefulProxy', wait=False,
                                      args=[proxies[start:end], ip_list, flag])
                start = end
                threads += 1
        create_thread_and_run(GetFreeProxy, 'validUsefulProxy', wait=False, args=[proxies[start:], ip_list, flag])

        while True:
            sleep(3)
            if len(flag) >= threads:
                break
        print('更新完成, 可用ip数: ', len(ip_list))
        GetFreeProxy.save_to_file(ip_list)

    @staticmethod
    def save_to_file(ip_list):
        file_path = os.path.join(os.path.dirname(__file__), './proxy_list')
        with open(file_path, 'w') as f:
            for ip in ip_list:
                f.write(ip+'\n')

    @staticmethod
    def get_list_proxies():
        """
            免费代理IP获取列表，根据需求删减
        :return:
        """
        proxies = []
        proxies.extend(GetFreeProxy.freeProxySecond())
        # proxies.extend(GetFreeProxy.freeProxyFourth())
        proxies.extend(GetFreeProxy.freeProxyFifth())
        # proxies.extend(GetFreeProxy.freeProxySixth())
        proxies.extend(GetFreeProxy.freeProxySeventh())
        # proxies.extend(GetFreeProxy.freeProxyEight())
        # proxies.extend(GetFreeProxy.freeProxyNinth())
        # proxies.extend(GetFreeProxy.freeProxyTen())
        proxies.extend(GetFreeProxy.freeProxyEleven())
        proxies.extend(GetFreeProxy.freeProxyTwelve())
        # proxies.extend(GetFreeProxy.freeProxyWallFirst())
        # proxies.extend(GetFreeProxy.freeProxyWallSecond())
        # proxies.extend(GetFreeProxy.freeProxyWallThird())
        return proxies


def check_ip_from_file():
    """
        对proxy_list文件中的代理ip进行可用性筛选
    :return:
    """
    proxy_list = []
    proxy_path = os.path.join(os.path.dirname(__file__), './proxy_list')
    try:
        with open(proxy_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for i in lines:
                p = i.strip("\n")
                proxy_list.append(p)
    except Exception:
        with open(proxy_path, "r", ) as f:
            lines = f.readlines()
            for i in lines:
                p = i.strip("\n")
                proxy_list.append(p)
    GetFreeProxy.check_ip_available(proxy_list, 10)


if __name__ == '__main__':
    # GetFreeProxy.getAllProxy()
    check_ip_from_file()
    pass
