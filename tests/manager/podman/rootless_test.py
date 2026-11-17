import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.manager.podman.rootless import not_supported_in_rootless
from src.Kathara.exceptions import NotSupportedError


def test_not_supported_in_rootless():
    with pytest.raises(NotSupportedError, match="Some feature is not supported by the Podman backend"):
        not_supported_in_rootless("Some feature")
