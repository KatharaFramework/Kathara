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

    def drop_privileges(self) -> None:
        logging.debug("Called `drop_privileges`...")

        logging.debug(f"Reference count is {self._ref}.")
        if self._ref > 1:
            self._ref -= 1
            logging.debug(f"Reference count is {self._ref}, exiting.")
            return

        if self._ref <= 0:
            self._ref = 0
            logging.debug(f"Reference count is {self._ref}, exiting.")
            return

        logging.debug(f"Dropping privileges to UID={self.user_uid} and GID={self.user_gid}...")

        try:
            os.setuid(self.user_uid)
        except OSError:
            pass

        try:
            os.setgid(self.user_gid)
        except OSError:
            pass

        self._ref = 0
        logging.debug(f"Reference count is reset to 0.")

    def raise_privileges(self) -> None:
        logging.debug("Called `raise_privileges`...")

        self._ref += 1
        logging.debug(f"Reference count is now {self._ref}.")
        if self._ref > 1:
            logging.debug("Reference count > 1, exiting.")
            return

        logging.debug(f"Raising privileges to UID={self.effective_user_uid} and GID={self.effective_user_gid}...")

        try:
            os.setuid(self.effective_user_uid)
        except OSError:
            pass

        try:
            os.setgid(self.effective_user_gid)
        except OSError:
            pass
