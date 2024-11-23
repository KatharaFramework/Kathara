from ..exceptions import InvalidDockerConfigJsonError
from ..setting.Setting import Setting
from ..trdparty.consolemenu.validators.base import BaseValidator


class DockerConfigJsonValidator(BaseValidator):
    def __init__(self) -> None:
        super(DockerConfigJsonValidator, self).__init__()

    def validate(self, input_string: str) -> bool:
        try:
            Setting.get_instance().check_docker_config_json(input_string)
            return True
        except (OSError, InvalidDockerConfigJsonError) as e:
            print(str(e))
            return False
