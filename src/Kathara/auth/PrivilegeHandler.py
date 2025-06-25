from __future__ import annotations

import logging
import os

from ..exceptions import InstantiationError


class PrivilegeHandler(object):
    __slots__ = ['user_uid', 'user_gid', 'effective_user_uid', 'effective_user_gid', '_ref']

    __instance: PrivilegeHandler = None

    @staticmethod
    def get_instance() -> PrivilegeHandler:
        if PrivilegeHandler.__instance is None:
            PrivilegeHandler()

        return PrivilegeHandler.__instance

    def __init__(self) -> None:
        if PrivilegeHandler.__instance is not None:
            raise InstantiationError("This class is a singleton!")
        else:
            try:
                self.user_uid: int = os.getuid()
                self.user_gid: int = os.getgid()

                self.effective_user_uid: int = os.geteuid()
                self.effective_user_gid: int = os.getegid()
            except AttributeError:
                pass

            self._ref = 0

            PrivilegeHandler.__instance = self

    def drop_effective_privileges(self) -> None:
        logging.debug("Called `drop_effective_privileges`...")
        try:
            os.seteuid(self.user_uid)
        except OSError:
            pass

        try:
            os.setegid(self.user_gid)
        except OSError:
            pass

    def drop_privileges(self) -> None:
        logging.debug(f"Calling `drop_privileges` with current values: "
                      f"UID={os.getuid()}, EUID={os.geteuid()}, GID={os.getgid()}, EGID={os.getegid()}...")

        logging.debug(f"Reference count is {self._ref}.")
        if self._ref > 1:
            self._ref -= 1
            logging.debug(f"Reference count is {self._ref}, exiting.")
            return

        if self._ref <= 0:
            self._ref = 0
            logging.debug(f"Reference count is {self._ref}, exiting.")
            return

        logging.debug(f"Dropping privileges to EUID={self.user_uid} and EGID={self.user_gid}...")

        self.drop_effective_privileges()

        self._ref = 0
        logging.debug(f"Reference count is reset to 0.")

        logging.debug(f"Privileges after `drop_privileges`: "
                      f"UID={os.getuid()}, EUID={os.geteuid()}, GID={os.getgid()}, EGID={os.getegid()}...")

    def raise_effective_privileges(self) -> None:
        logging.debug("Called `raise_effective_privileges`...")
        try:
            os.seteuid(self.effective_user_uid)
        except OSError:
            pass

        try:
            os.setegid(self.effective_user_gid)
        except OSError:
            pass

    def raise_privileges(self) -> None:
        logging.debug(f"Calling `raise_privileges` with current values: "
                      f"UID={os.getuid()}, EUID={os.geteuid()}, GID={os.getgid()}, EGID={os.getegid()}...")

        self._ref += 1
        logging.debug(f"Reference count is now {self._ref}.")
        if self._ref > 1:
            if os.getegid() == self.user_gid:
                logging.debug("Reference count > 1, but EGID not set for the thread. Raising privileges...")
                self.raise_effective_privileges()
            else:
                logging.debug("Reference count > 1 with privileges already correct, exiting.")
            return

        logging.debug(f"Raising privileges to EUID={self.effective_user_uid} and EGID={self.effective_user_gid}...")

        self.raise_effective_privileges()

        logging.debug(f"Privileges after `raise_privileges`: "
                      f"UID={os.getuid()}, EUID={os.geteuid()}, GID={os.getgid()}, EGID={os.getegid()}...")
