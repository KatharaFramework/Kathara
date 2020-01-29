# Generic Exceptions
class HTTPConnectionError(Exception):
    pass


class SettingsError(Exception):
    def __init__(self, message):
        super().__init__("Settings file is not valid: %s\nFix it or delete it before launching." % message)


class DockerDaemonConnectionError(Exception):
    pass


# OS Exceptions
class PrivilegeError(Exception):
    pass


# Machine Exceptions
class MountDeniedError(Exception):
    pass


class MachineAlreadyExistsError(Exception):
    pass


class NonSequentialMachineInterfaceError(Exception):
    pass


class MachineOptionError(Exception):
    pass


# Test Exceptions
class TestError(Exception):
    pass


class MachineSignatureNotFoundError(TestError):
    pass
