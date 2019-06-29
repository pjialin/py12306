# coding: utf-8
import cv2, os
import numpy as np
from keras import models
from py12306.log.common_log import CommonLog


def get_text(img, offset=0):
    text = img[3:22, 120 + offset:177 + offset]
    text = cv2.cvtColor(text, cv2.COLOR_BGR2GRAY)
    text = text / 255.0
    h, w = text.shape
    text.shape = (1, h, w, 1)
    return text


def get_coordinate(fn):
    # 储存最终坐标结果
    result = ''

    try:
        # 读取并预处理验证码
        img = cv2.imread(fn)
        text = get_text(img)
        imgs = np.array(list(_get_imgs(img)))
        imgs = preprocess_input(imgs)

        # 识别文字
        model = models.load_model('py12306/helpers/ocr/model.v2.0.h5')
        label = model.predict(text)
        label = label.argmax()
        fp = open('py12306/helpers/ocr/texts.txt', encoding='utf-8')
        texts = [text.rstrip('\n') for text in fp]
        text = texts[label]

        # list放文字
        titles = [text]

        position = []

        # 获取下一个词
        # 根据第一个词的长度来定位第二个词的位置
        if len(text) == 1:
            offset = 27
        elif len(text) == 2:
            offset = 47
        else:
            offset = 60
        text2 = get_text(img, offset=offset)
        if text2.mean() < 0.95:
            label = model.predict(text2)
            label = label.argmax()
            text2 = texts[label]
            titles.append(text2)

        # 加载图片分类器
        model = models.load_model('py12306/helpers/ocr/12306.image.model.h5')
        labels = model.predict(imgs)
        labels = labels.argmax(axis=1)

        for pos, label in enumerate(labels):
            # print(pos // 4, pos % 4, texts[label])
            if len(titles) == 1:
                if texts[label] == titles[0]:
                    position.append(pos)
            elif len(titles) == 2:
                if texts[label] == titles[0]:
                    position.append(pos)
                elif texts[label] == titles[1]:
                    position.append(pos)
            elif len(titles) == 3:
                if texts[label] == titles[0]:
                    position.append(pos)
                elif texts[label] == titles[1]:
                    position.append(pos)
                elif texts[label] == titles[2]:
                    position.append(pos)

        # 没有识别到结果
        if len(position) == 0:
            return result

        for i in position:
            if i == 0:
                result += '31,45,'
            elif i == 1:
                result += '100,45,'
            elif i == 2:
                result += '170,45,'
            elif i == 3:
                result += '240,45,'
            elif i == 4:
                result += '30,115,'
            elif i == 5:
                result += '100,115,'
            elif i == 6:
                result += '170,115,'
            elif i == 7:
                result += '240,115,'
        result = result[:-1]
    except:
        CommonLog.print_auto_code_fail(CommonLog.MESSAGE_GET_RESPONSE_FROM_FREE_AUTO_CODE)
    return result


def preprocess_input(x):
    x = x.astype('float32')
    # 我是用cv2来读取的图片，其已经是BGR格式了
    mean = [103.939, 116.779, 123.68]
    x -= mean
    return x


def _get_imgs(img):
    interval = 5
    length = 67
    for x in range(40, img.shape[0] - length, interval + length):
        for y in range(interval, img.shape[1] - length, interval + length):
            yield img[x:x + length, y:y + length]


if __name__ == '__main__':
    print(get_coordinate('a.jpg'))
