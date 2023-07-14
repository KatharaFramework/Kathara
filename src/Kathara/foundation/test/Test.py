import os
from abc import ABC, abstractmethod
from typing import Dict, Union, List

import chardet
from deepdiff import DeepDiff

from ...manager.Kathara import Kathara
from ...model.Lab import Lab


class Test(ABC):
    __slots__ = ['lab', 'test_path', 'signature_path', 'results_path']

    def __init__(self, lab: Lab) -> None:
        self.lab: Lab = lab
        self.test_path: str = os.path.join(self.lab.fs_path(), '_test')

        self.signature_path: str = os.path.join(self.test_path, 'signature')
        self.results_path: str = os.path.join(self.test_path, 'results')

    @abstractmethod
    def create_signature(self) -> None:
        raise NotImplementedError("You must implement `create_signature` method.")

    @abstractmethod
    def test(self) -> bool:
        raise NotImplementedError("You must implement `test` method.")

    @abstractmethod
    def check_signature(self, signature: Union[Dict, str], status: Union[Dict, str]) -> Union[DeepDiff, List]:
        raise NotImplementedError("You must implement `check_signature` method.")

    @staticmethod
    def _get_machine_command_output(lab_hash, machine_name, command):
        exec_output = Kathara.get_instance().exec(machine_name, command, lab_hash=lab_hash)

        result = {
            'stdout': '',
            'stderr': ''
        }

        try:
            while True:
                (stdout, stderr) = next(exec_output)

                stdout_char_encoding = chardet.detect(stdout) if stdout else None
                stderr_char_encoding = chardet.detect(stderr) if stderr else None

                if stdout:
                    result['stdout'] += stdout.decode(stdout_char_encoding['encoding']) if stdout else ""
                if stderr:
                    result['stderr'] += stderr.decode(stderr_char_encoding['encoding']) if stderr else ""
        except StopIteration:
            return result['stdout'], result['stderr']
