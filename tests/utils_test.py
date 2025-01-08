import sys

sys.path.insert(0, './')

from src.Kathara.utils import parse_docker_engine_version


def test_docker_engine_version_numbers_only():
    assert parse_docker_engine_version('20.10.05') == '20.10.05'


def test_docker_engine_version_debian_str_plus():
    assert parse_docker_engine_version('20.10.5+dfsg1') == '20.10.5'


def test_docker_engine_version_debian_str_tilde():
    assert parse_docker_engine_version('20.10.5~dfsg1') == '20.10.5'


def test_docker_engine_version_debian_str_nosep():
    assert parse_docker_engine_version('20.10.5dfsg1') == '20.10.5'
