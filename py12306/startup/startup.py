#!/usr/bin/env python
# encoding: utf-8
'''
@author: Hamish Zou
@license: Apache License 2.0
@contact: hamish.zou@outlook.com
@software: JetBrains PyCharm
@file: startup.py
@time: 18/1/2019 13:42
@desc:
'''


class StartUp():
    @staticmethod
    def start_up():
        confirmation = input("是模式會覆寫原有配置檔，是否確定？(y/n)：")
        if confirmation == "y":
            pass
        else:
            print("正在退出...")
            exit(1)
        USER_ACCOUNTS = {'key': 0, 'user_name': input("請鍵入12306用戶名："), 'password': input("請鍵入12306密碼：")}
        USER_ACCOUNTS1 = '[' + str(USER_ACCOUNTS) + ']'

        QUERY_INTERVAL = (input("請輸入查詢間隔（單位為秒）："))

        USER_HEARTBEAT_INTERVAL = (input("請輸入用戶心跳檢測間隔（單位為秒）："))

        QUERY_JOB_THREAD_ENABLED = (input("是否啟用多線程查詢（0為禁用，1為啟用）？"))

        AUTO_CODE_PLATFORM = input("請選擇驗證碼識別平台，free為免費平台，ruokuai為若快平台（註冊地址見github）：")
        if AUTO_CODE_PLATFORM == 'ruokuai':
            AUTO_CODE_ACCOUNT = {'user': input("請輸入若快平台用戶名："), 'pwd': input("請輸入若快平台密碼：")}
            AUTO_CODE_ACCOUNT1 = str(AUTO_CODE_ACCOUNT)
        else:
            AUTO_CODE_ACCOUNT1 = str({})

        # 禁用所有通知、輸出日誌、集群
        BAN = "NOTIFICATION_BY_VOICE_CODE = 0\n\
DINGTALK_ENABLED = 0\n\
TELEGRAM_ENABLED = 0\n\
SERVERCHAN_ENABLED = 0\n\
PUSHBEAR_ENABLED = 0\n\
OUT_PUT_LOG_TO_FILE_ENABLED = 0\n\
CLUSTER_ENABLED = 0\n\
EMAIL_ENABLED = 0"

        WEB = "WEB_ENABLE = 1\n\
WEB_USER = {\n\
    'username': 'admin',\n\
    'password': '123456'\n\
}\n\
WEB_PORT = 8008"

        print("已禁用所有通知、輸出日誌、集群功能。")
        print("已開啟本地WEB管理，網址為127.0.0.1:8008，用戶名為admin，密碼為123456")

        QUERY_JOBS = {'job_name': input("請輸入任務名："), 'account_key': 0}
        left_dates = input("請輸入出發日期，格式為YYYY-MM-DD：")
        QUERY_JOBS['left_dates'] = left_dates.split()
        QUERY_JOBS_STATIONS = {'left': input("請輸入出發車站："), 'arrive': input("請輸入目的車站：")}
        QUERY_JOBS['stations'] = QUERY_JOBS_STATIONS
        QUERY_JOBS_MEMBERS = input("請輸入乘客姓名，購買兒童票設置二相同姓名即可，兩姓名之間請用空格隔開：")
        QUERY_JOBS_MEMBERS1 = QUERY_JOBS_MEMBERS.split(' ')
        QUERY_JOBS['members'] = QUERY_JOBS_MEMBERS1
        QUERY_JOBS_ALLOW_LESS_MEMBER = int(input("是否允許餘票不足時提交部分乘客（0為禁用，1為啟用）？"))
        QUERY_JOBS['allow_less_member'] = QUERY_JOBS_ALLOW_LESS_MEMBER
        QUERY_JOBS_SEATS = input("篩選席位，有先後順序，可用值: 特等座, 商务座, 一等座, 二等座, 软卧, 硬卧, 动卧, 软座, 硬座, 无座，不同席位之間請用空格隔開：")
        QUERY_JOBS_SEATS1 = QUERY_JOBS_SEATS.split(' ')
        QUERY_JOBS['seats'] = QUERY_JOBS_SEATS1
        QUERY_JOBS_TRAIN_NUMBERS = input("請輸入車次，為空時所有車次都可提交，請注意大小寫需要保持一致，車次間用空格隔開：")
        QUERY_JOBS_TRAIN_NUMBERS1 = QUERY_JOBS_TRAIN_NUMBERS.split(' ')
        QUERY_JOBS['train_numbers'] = QUERY_JOBS_TRAIN_NUMBERS1
        QUERY_JOBS1 = '[' + str(QUERY_JOBS) + ']'

        file = open('env.py', 'w+')
        file.write(
            'USER_ACCOUNTS = ' + USER_ACCOUNTS1 + '\n' + 'QUERY_INTERVAL = ' + QUERY_INTERVAL + '\n' + \
            'USER_HEARTBEAT_INTERVAL = ' + USER_HEARTBEAT_INTERVAL + '\n' + 'QUERY_JOB_THREAD_ENABLED = ' + \
            QUERY_JOB_THREAD_ENABLED + '\n' + "AUTO_CODE_PLATFORM = '" + AUTO_CODE_PLATFORM + "'\n" + \
            'AUTO_CODE_ACCOUNT1 = ' + AUTO_CODE_ACCOUNT1 + '\n' + BAN + '\n' + WEB + '\n' + 'QUERY_JOBS = ' + QUERY_JOBS1)
