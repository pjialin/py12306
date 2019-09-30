import math
import random

from py12306.config import Config
from py12306.helpers.api import API_FREE_CODE_QCR_API
from py12306.helpers.request import Request
from py12306.log.common_log import CommonLog
#from py12306.vender.ruokuai.main import RKClient


class OCR:
    """
    图片识别
    """
    session = None

    def __init__(self):
        self.session = Request()

    @classmethod
    def get_img_position(cls, img):
        """
        获取图像坐标
        :param img_path:
        :return:
        """
        self = cls()
        if Config().AUTO_CODE_PLATFORM == 'free':
            return self.get_image_by_free_site(img)
        return self.get_image_by_ml(img)

    def get_image_position_by_offset(self, offsets):
        positions = []
        width = 75
        height = 75
        for offset in offsets:
            random_x = random.randint(-5, 5)
            random_y = random.randint(-5, 5)
            offset = int(offset)
            x = width * ((offset - 1) % 4 + 1) - width / 2 + random_x
            y = height * math.ceil(offset / 4) - height / 2 + random_y
            positions.append(int(x))
            positions.append(int(y))
        return positions

    def get_image_by_free_site(self, img):
        data = {
            'img': img
        }
        response = self.session.post(API_FREE_CODE_QCR_API, data=data, timeout=30)
        result = response.json()
        if result.get('msg') == 'success':
            pos = result.get('result')
            return self.get_image_position_by_offset(pos)

        CommonLog.print_auto_code_fail(CommonLog.MESSAGE_GET_RESPONSE_FROM_FREE_AUTO_CODE)
        return None

    def get_image_by_ml(self, img):
        from py12306.helpers.ocr.ml_predict import get_coordinate
        import base64

        result = get_coordinate(base64.b64decode(img))
        result = self.get_image_position_by_offset(result)
        # CommonLog.print_auth_code_info("验证码识别的结果为：" + result)
        if result:
            return result

if __name__ == '__main__':
    pass
    # code_result = AuthCode.get_auth_code()
