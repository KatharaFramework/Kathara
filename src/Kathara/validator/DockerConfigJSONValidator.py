from ..exceptions import InvalidDockerConfigJSONError
from ..setting.Setting import Setting
from ..trdparty.consolemenu.validators.base import BaseValidator


class DockerConfigJSONValidator(BaseValidator):
    def __init__(self) -> None:
        super(DockerConfigJSONValidator, self).__init__()

    def validate(self, input_string: str) -> bool:
        try:
            Setting.get_instance().check_docker_config_json(input_string)
            return True
        except (OSError, InvalidDockerConfigJSONError) as e:
            print(str(e))
            return False
