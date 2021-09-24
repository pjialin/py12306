# -*- coding: utf-8 -*-

import os
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
            for k in range(info['planes']):
                px = lines[i][j * info['planes'] + k]
                total += px
            avg = total / info['planes']
            mid = (2 ** info['bitdepth']) / 2
            black = avg < mid
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

    if os.name == 'nt':
        white_block = '▇▇'
        black_block = '  '
        new_line = '\n'
    else:
        white_block = '\033[0;37;47m  '
        black_block = '\033[0;37;40m  '
        new_line = '\033[0m\n'

    print('', flush=False)
    for i in range(module_count + 2):
        print(white_block, end='', flush=False)
    print('', end=new_line, flush=False)
    i = y_flag
    while i < height - y_flag:
        print(white_block, end='', flush=False)
        j = x_flag
        while j < width - x_flag:
            total = 0
            for k in range(info['planes']):
                px = lines[i][j * info['planes'] + k]
                total += px
            avg = total / info['planes']
            mid = (2 ** info['bitdepth']) / 2
            black = avg < mid
            if black:
                print(black_block, end='', flush=False)
            else:
                print(white_block, end='', flush=False)
            j += scale
        print(white_block, end=new_line, flush=False)
        i += scale
    for i in range(module_count + 2):
        print(white_block, end='', flush=False)
    print('', end=new_line, flush=True)
