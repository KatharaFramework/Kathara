import difflib
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

    @staticmethod
    def check_signature(signature, status):
        # Clean strings, by removing trailing slashes and spaces (using IS_CHARACTER_JUNK)
        signature = signature.splitlines()
        status = status.splitlines()

        # Do the diff between the arrays, n=0 removes context strings
        diff = difflib.unified_diff(signature, status, n=0, lineterm="")
        # Remove headers of the diff from the result
        return [filter(lambda x: not x.startswith(('---', '+++', '@@')), diff)]
