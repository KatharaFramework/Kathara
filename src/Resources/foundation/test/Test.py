import os
from abc import ABC, abstractmethod


class Test(ABC):
    __slots__ = ['lab', 'test_path', 'signature_path', 'results_path']

    def __init__(self, lab):
        self.lab = lab
        self.test_path = os.path.join(self.lab.path, '_test')

        self.signature_path = os.path.join(self.test_path, 'signature')
        self.results_path = os.path.join(self.test_path, 'results')

    @abstractmethod
    def create_signature(self):
        raise NotImplementedError("You must implement `create_signature` method.")

    @abstractmethod
    def test(self):
        raise NotImplementedError("You must implement `test` method.")

    @abstractmethod
    def check_signature(self, signature, status):
        raise NotImplementedError("You must implement `check_signature` method.")
