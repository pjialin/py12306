# coding: utf-8
import cv2, os
import tensorflow as tf
import numpy as np
from keras import models
from py12306.log.common_log import CommonLog
from py12306.config import Config

tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)


def get_text(img, offset=0):
    text = img[3:22, 120 + offset:177 + offset]
    text = cv2.cvtColor(text, cv2.COLOR_BGR2GRAY)
    text = text / 255.0
    h, w = text.shape
    text.shape = (1, h, w, 1)
    return text


def get_coordinate(img_str):
    # 储存最终坐标结果
    result = ''
    orc_dir = '%spy12306/helpers/ocr/' % Config.PROJECT_DIR

    try:
        # 读取并预处理验证码
        img = cv2.imdecode(np.fromstring(img_str, np.uint8), cv2.IMREAD_COLOR)
        text = get_text(img)
        imgs = np.array(list(_get_imgs(img)))
        imgs = preprocess_input(imgs)

        # 识别文字
        model = models.load_model('%smodel.v2.0.h5' % orc_dir, compile=False)
        label = model.predict(text)
        label = label.argmax()
        fp = open('%stexts.txt' % orc_dir, encoding='utf-8')
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
        model = models.load_model('%s12306.image.model.h5' % orc_dir, compile=False)
        labels = model.predict(imgs)
        labels = labels.argmax(axis=1)

        for pos, label in enumerate(labels):
            if texts[label] in titles:
                position.append(pos + 1)

        # 没有识别到结果
        if len(position) == 0:
            return result
        result = position
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
    with open('a.jpg', 'r') as f:
        print(get_coordinate(f.buffer.read()))
