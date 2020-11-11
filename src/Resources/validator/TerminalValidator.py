from ..setting.Setting import Setting

from ..trdparty.consolemenu.validators.base import BaseValidator


class TerminalValidator(BaseValidator):
    def __init__(self):
        super(TerminalValidator, self).__init__()

    def validate(self, input_string):
        try:
            return Setting.get_instance().check_terminal(input_string)
        except Exception:
            return False
