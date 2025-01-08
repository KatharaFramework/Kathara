import json
import os.path

from ..trdparty.consolemenu.validators.base import BaseValidator


class DockerConfigJsonValidator(BaseValidator):
    def __init__(self) -> None:
        super(DockerConfigJsonValidator, self).__init__()

    def validate(self, input_string: str) -> bool:
        try:
            with open(os.path.expanduser(input_string), 'r') as docker_config_json_file:
                json.load(docker_config_json_file)
            return True
        except (OSError, ValueError) as e:
            print(str(e))
            return False
