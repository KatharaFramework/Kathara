import logging
import os


class PrivilegeHandler(object):
    __slots__ = ['user_uid', 'user_gid', 'effective_user_uid', 'effective_user_gid']

    __instance = None

    @staticmethod
    def get_instance():
        if PrivilegeHandler.__instance is None:
            PrivilegeHandler()

        return PrivilegeHandler.__instance

    def __init__(self):
        if PrivilegeHandler.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            try:
                self.user_uid = os.getuid()
                self.user_gid = os.getgid()

                self.effective_user_uid = os.geteuid()
                self.effective_user_gid = os.getegid()
            except AttributeError:
                pass

            PrivilegeHandler.__instance = self

    def drop_privileges(self):
        logging.debug("Dropping privileges to UID=%d and GID=%d..." % (self.user_uid, self.user_gid))

        try:
            os.setuid(self.user_uid)
        except OSError:
            pass

        try:
            os.setgid(self.user_gid)
        except OSError:
            pass

    def raise_privileges(self):
        logging.debug("Raising privileges to UID=%d and GID=%d..." % (self.effective_user_uid, self.effective_user_gid))

        try:
            os.setuid(self.effective_user_uid)
        except OSError:
            pass

        try:
            os.setgid(self.effective_user_gid)
        except OSError:
            pass
