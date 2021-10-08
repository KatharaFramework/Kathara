from typing import Callable, Any

from . import utils
from .auth.PrivilegeHandler import PrivilegeHandler


def privileged(method: Callable) -> Any:
    """Decorator function to execute a method with proper privileges. They are then dropped when method is executed."""

    def exec_with_privileges(*args, **kw):
        utils.exec_by_platform(PrivilegeHandler.get_instance().raise_privileges, lambda: None, lambda: None)
        result = method(*args, **kw)
        utils.exec_by_platform(PrivilegeHandler.get_instance().drop_privileges, lambda: None, lambda: None)

        return result

    return exec_with_privileges
