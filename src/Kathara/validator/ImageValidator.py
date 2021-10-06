from ..setting.Setting import Setting
from ..trdparty.consolemenu.validators.base import BaseValidator


class ImageValidator(BaseValidator):
    def __init__(self) -> None:
        super(ImageValidator, self).__init__()

    def validate(self, input_string: str) -> bool:
        try:
            Setting.get_instance().check_image(input_string)
            return True
        except Exception:
            return False
