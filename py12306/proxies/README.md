# 代理使用

## 方式
1. 使用代理池 [proxy_pool](https://github.com/jhao104/proxy_pool)

    自己按照教程进行搭建，然后在配置文件设置API端口，同时在 `env.py` 中将PROXY_TYPE设置为1
     
    经过测试由于使用的是免费代理，所以连接速度和质量不是很高。

2. 使用`proxy_list`文件

    在`proxy_list`文件中放入代理IP，同时在 `env.py` 中将PROXY_TYPE设置为2

## 免费IP获取
运行`proxy_tool.py` (需要按照需求更改main里边的方法)

使用该方法会将测试可用的ip保存到proxy_list文件中

## 代理测试
运行 `proxy_test.py` 文件，能够直观的看到是否代理成功