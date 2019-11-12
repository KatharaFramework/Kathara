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
        signature = ["".join([y for y in filter(lambda z: not difflib.IS_CHARACTER_JUNK(z), x)])
                     for x in map(lambda x: x.strip(), signature.splitlines())
                     ]
        status = ["".join([y for y in filter(lambda z: not difflib.IS_CHARACTER_JUNK(z), x)])
                  for x in map(lambda x: x.strip(), status.splitlines())
                  ]

        # Do the diff between the arrays, n=0 removes context strings
        diff = difflib.unified_diff(signature, status, n=0, lineterm="")
        # Remove headers of the diff from the result
        diff = filter(lambda x: not x.startswith(('---', '+++', '@@')), diff)

        return [x for x in diff]
