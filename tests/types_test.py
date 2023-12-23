import sys

sys.path.insert(0, './')

from src.Kathara.types import SharedCollisionDomainsOption


def test_shared_collision_domains_option_to_string():
    assert SharedCollisionDomainsOption.to_string(1) == 'Not Shared'
    assert SharedCollisionDomainsOption.to_string(2) == 'Share collision domains between network scenarios'
    assert SharedCollisionDomainsOption.to_string(3) == 'Share collision domains between users'
