from consolemenu.validators.base import BaseValidator
from ..setting.Setting import Setting

class ImageValidator(BaseValidator):

    def __init__(self):
        """
        URL Validator class
        """
        super(ImageValidator, self).__init__()

    def validate(self, input_string):
        """
        Validate url
        :return: True if match / False otherwise
        """
        try:
            Setting.get_instance().image = input_string
            Setting.get_instance().check()
            Setting.get_instance().save_selected(['image'])
            return True
        except:
            return False