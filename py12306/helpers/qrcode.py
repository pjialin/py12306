# -*- coding: utf-8 -*-

import png


def print_qrcode(path):
    """
    将二维码输出到控制台
    需要终端尺寸足够大才能显示

    :param path: 二维码图片路径 (PNG 格式)
    :return: None
    """
    reader = png.Reader(path)
    width, height, rows, info = reader.read()
    lines = list(rows)

    planes = info['planes']  # 通道数
    threshold = (2 ** info['bitdepth']) / 2  # 色彩阈值

    # 识别二维码尺寸
    x_flag = -1   # x 边距标志
    y_flag = -1   # y 边距标志
    x_white = -1  # 定位图案白块 x 坐标
    y_white = -1  # 定位图案白块 y 坐标

    i = y_flag
    while i < height:
        if y_white > 0 and x_white > 0:
            break
        j = x_flag
        while j < width:
            total = 0
            for k in range(planes):
                px = lines[i][j * planes + k]
                total += px
            avg = total / planes
            black = avg < threshold
            if y_white > 0 and x_white > 0:
                break
            if x_flag > 0 > x_white and not black:
                x_white = j
            if x_flag == -1 and black:
                x_flag = j
            if y_flag > 0 > y_white and not black:
                y_white = i
            if y_flag == -1 and black:
                y_flag = i
            if x_flag > 0 and y_flag > 0:
                i += 1
            j += 1
        i += 1

    assert y_white - y_flag == x_white - x_flag
    scale = y_white - y_flag

    assert width - x_flag == height - y_flag
    module_count = int((width - x_flag * 2) / scale)

    whole_white = '█'
    whole_black = ' '
    down_black = '▀'
    up_black = '▄'

    dual_flag = False
    last_line = []
    output = '\n'
    for i in range(module_count + 2):
        output += up_black
    output += '\n'
    i = y_flag
    while i < height - y_flag:
        if dual_flag:
            output += whole_white
        t = 0
        j = x_flag
        while j < width - x_flag:
            total = 0
            for k in range(planes):
                px = lines[i][j * planes + k]
                total += px
            avg = total / planes
            black = avg < threshold
            if dual_flag:
                last_black = last_line[t]
                if black and last_black:
                    output += whole_black
                elif black and not last_black:
                    output += down_black
                elif not black and last_black:
                    output += up_black
                elif not black and not last_black:
                    output += whole_white
            else:
                last_line[t:t+1] = [black]
            t = t + 1
            j += scale
        if dual_flag:
            output += whole_white + '\n'
        dual_flag = not dual_flag
        i += scale
    output += whole_white
    for i in range(module_count):
        output += up_black if last_line[i] else whole_white
    output += whole_white + '\n'
    print(output, flush=True)
