import math
import random

from py12306.config import Config
from py12306.helpers.api import API_FREE_CODE_QCR_API
from py12306.helpers.request import Request
from py12306.log.common_log import CommonLog
from py12306.vender.ruokuai.main import RKClient


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
        if Config().AUTO_CODE_PLATFORM == 'free' or Config().AUTO_CODE_PLATFORM == 'user':
            return self.get_image_by_free_site(img)
        return self.get_img_position_by_ruokuai(img)

    def get_img_position_by_ruokuai(self, img):
        ruokuai_account = Config().AUTO_CODE_ACCOUNT
        soft_id = '119671'
        soft_key = '6839cbaca1f942f58d2760baba5ed987'
        rc = RKClient(ruokuai_account.get('user'), ruokuai_account.get('pwd'), soft_id, soft_key)
        result = rc.rk_create(img, 6113)
        if "Result" in result:
            return self.get_image_position_by_offset(list(result['Result']))
        CommonLog.print_auto_code_fail(result.get("Error", CommonLog.MESSAGE_RESPONSE_EMPTY_ERROR))
        return None

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
        if Config().AUTO_CODE_PLATFORM == 'free':
           response = self.session.post(API_FREE_CODE_QCR_API, data=data, timeout=30)
        else:
           response = self.session.post(Config().API_USER_CODE_QCR_API, data=data, timeout=30)
        result = response.json()
        if result.get('msg') == 'success':
            pos = result.get('result')
            return self.get_image_position_by_offset(pos)

        CommonLog.print_auto_code_fail(CommonLog.MESSAGE_GET_RESPONSE_FROM_FREE_AUTO_CODE)
        return None


if __name__ == '__main__':
    pass
    # code_result = AuthCode.get_auth_code()
