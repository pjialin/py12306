import math
import random

from py12306.config import Config
from py12306.log.common_log import CommonLog
from py12306.vender.ruokuai.main import RKClient


class OCR:
    """
    图片识别
    """

    @classmethod
    def get_img_position(cls, img_path):
        """
        获取图像坐标
        :param img_path:
        :return:
        """
        self = cls()
        return self.get_img_position_by_ruokuai(img_path)

    def get_img_position_by_ruokuai(self, img_path):
        ruokuai_account = Config().AUTO_CODE_ACCOUNT
        soft_id = '119671'
        soft_key = '6839cbaca1f942f58d2760baba5ed987'
        rc = RKClient(ruokuai_account.get('user'), ruokuai_account.get('pwd'), soft_id, soft_key)
        im = open(img_path, 'rb').read()
        result = rc.rk_create(im, 6113)
        if "Result" in result:
            return self.get_image_position_by_offset(list(result['Result']))
        CommonLog.print_auto_code_fail(result.get("Error", '-'))
        return None

    def get_image_position_by_offset(self, offsets):
        positions = []
        width = 70
        height = 70
        random_num = random.randint(0, 8)
        for offset in offsets:
            offset = int(offset)
            x = width * (offset % 5) - width / 2 + random_num
            y = height * math.ceil(offset / 4) - height / 2 - random_num
            positions.append(int(x))
            positions.append(int(y))
        return positions


if __name__ == '__main__':
    pass
    # code_result = AuthCode.get_auth_code()
