import sys

import pytest

sys.path.insert(0, './')

from src.Kathara.utils import parse_docker_engine_version, parse_uint


def test_docker_engine_version_numbers_only():
    assert parse_docker_engine_version('20.10.05') == '20.10.05'


def test_docker_engine_version_debian_str_plus():
    assert parse_docker_engine_version('20.10.5+dfsg1') == '20.10.5'


def test_docker_engine_version_debian_str_tilde():
    assert parse_docker_engine_version('20.10.5~dfsg1') == '20.10.5'


def test_docker_engine_version_debian_str_nosep():
    assert parse_docker_engine_version('20.10.5dfsg1') == '20.10.5'


@pytest.mark.parametrize("value, expected", [
    (0, 0),
    (42, 42),
    ("42", 42),
    ("  42 ", 42),
    ("007", 7),
    ("0x4000", 0x4000),
    ("0XfF", 255),
    (2 ** 64 - 1, 2 ** 64 - 1),
])
def test_parse_uint(value, expected):
    assert parse_uint(value) == expected


@pytest.mark.parametrize("value", ["", "abc", "1.5", "0x", "0xZZ", "1e3", 1.5, True, False, None, [1]])
def test_parse_uint_not_an_integer(value):
    with pytest.raises(ValueError, match="is not an integer"):
        parse_uint(value)


@pytest.mark.parametrize("value, bit_size, max_value", [
    (-1, 64, 2 ** 64 - 1),
    ("-1", 64, 2 ** 64 - 1),
    (2 ** 64, 64, 2 ** 64 - 1),
    (2 ** 32, 32, 2 ** 32 - 1),
    ("0x10000", 16, 2 ** 16 - 1),
    (256, 8, 255),
])
def test_parse_uint_out_of_range(value, bit_size, max_value):
    with pytest.raises(ValueError, match=f"between 0 and {max_value}"):
        parse_uint(value, bit_size=bit_size)


@pytest.mark.parametrize("value, bit_size", [(0, 8), (255, 8), ("0xFFFF", 16), (2 ** 32 - 1, 32)])
def test_parse_uint_bit_size_boundaries(value, bit_size):
    assert parse_uint(value, bit_size=bit_size) == (int(value, 16) if isinstance(value, str) else value)
