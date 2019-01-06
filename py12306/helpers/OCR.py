from py12306 import config
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
        pass

    def get_img_position_by_ruokuai(self, img_path):
        ruokuai_account = config.AUTO_CODE_ACCOUNT
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
        for offset in offsets:
            if offset == '1':
                y = 46
                x = 42
            elif offset == '2':
                y = 46
                x = 105
            elif offset == '3':
                y = 45
                x = 184
            elif offset == '4':
                y = 48
                x = 256
            elif offset == '5':
                y = 36
                x = 117
            elif offset == '6':
                y = 112
                x = 115
            elif offset == '7':
                y = 114
                x = 181
            elif offset == '8':
                y = 111
                x = 252
            else:
                pass
            positions.append(x)
            positions.append(y)
        return positions



if __name__ == '__main__':
    pass
    # code_result = AuthCode.get_auth_code()
