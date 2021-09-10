import os
from abc import ABC, abstractmethod
from typing import Dict, Union, List

from deepdiff import DeepDiff

from ...model.Lab import Lab


class Test(ABC):
    __slots__ = ['lab', 'test_path', 'signature_path', 'results_path']

    def __init__(self, lab: Lab) -> None:
        self.lab: Lab = lab
        self.test_path: str = os.path.join(self.lab.path, '_test')

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
