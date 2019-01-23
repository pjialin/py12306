from py12306.helpers.request import Request
from py12306.config import Config


def test():
    session = Request(True)
    Config().PROXY_ENABLE = 0
    ip_1 = session.get(url='http://icanhazip.com/').text.strip('\n')
    print('代理前ip: \'{}\''.format(ip_1))
    Config().PROXY_ENABLE = 1
    print('使用代理： {}'.format(session.get_proxy()))
    for i in range(1, 4):
        ip_2 = session.get(url='http://icanhazip.com/').text.strip('\n')
        print('代理后ip: \'{}\''.format(ip_2))

    if ip_1 != ip_2:
        print('代理成功')


if __name__ == '__main__':
    test()
