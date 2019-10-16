from .. import utils

import os
import logging

class PrivilegeManager():
    __slots__ = ['manager', 'user_uid', 'user_gid', 'raised_uid', 'raised_gid']

    __instance = None

    @staticmethod
    def get_instance():
        if PrivilegeManager.__instance is None:
            PrivilegeManager()

        return PrivilegeManager.__instance

    def __init__(self):
        if PrivilegeManager.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self.user_uid = os.getuid()
            self.user_gid = os.getgid()

            self.raised_uid = os.geteuid()
            self.raised_gid = os.getegid()

            PrivilegeManager.__instance = self


    def drop_privileges(self):
        logging.debug("Dropping privileges...")
        try:
            os.setgid(self.user_gid)
        except Exception:
            pass

        try:
            os.setuid(self.user_uid)
        except Exception:
            pass

    def raise_privileges(self):
        logging.debug("Raising privileges...")
        try:
            os.setgid(self.raised_gid)
        except Exception:
            pass

        try:
            os.setuid(self.raised_uid)
        except Exception:
            pass