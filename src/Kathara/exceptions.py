# Generic Exceptions
class ClassNotFoundError(Exception):
    pass


class HTTPConnectionError(Exception):
    pass


class InstantiationError(Exception):
    pass


class InvocationError(Exception):
    pass


# Settings Exceptions
class SettingsError(Exception):
    def __init__(self, message) -> None:
        super().__init__("Settings file is not valid: %s\nFix it or delete it before launching." % message)


class SettingsNotFoundError(Exception):
    pass


class DockerDaemonConnectionError(Exception):
    pass


class NotSupportedError(Exception):
    def __init__(self, message) -> None:
        super().__init__("Not Supported: %s" % message)


# OS Exceptions
class PrivilegeError(Exception):
    pass


class InterfaceNotFoundError(Exception):
    pass


# Lab Exceptions
class LabAlreadyExistsError(Exception):
    pass


class LabNotFoundError(Exception):
    pass


class EmptyLabError(Exception):
    pass


class MachineDependencyError(Exception):
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


class MachineCollisionDomainConflictError(Exception):
    pass


class MachineNotFoundError(Exception):
    pass


class MachineNotReadyError(Exception):
    pass


# Link Exceptions
class LinkNotFoundError(Exception):
    pass


# Architecture Excpetion
class ArchitectureError(Exception):
    pass


# Test Exceptions
class TestError(Exception):
    pass


class MachineSignatureNotFoundError(TestError):
    pass


# Docker Exceptions
class InvalidImageArchitectureError(ValueError):
    __slots__ = ['image_name', 'arch']

    def __init__(self, image_name, arch):
        self.image_name = image_name
        self.arch = arch

    def __str__(self):
        return f"Docker Image `{self.image_name}` is not compatible with your host architecture `{self.arch}`"


class DockerImageNotFoundError(Exception):
    pass


class DockerPluginError(Exception):
    pass


# Kubernetes Exception
class KubernetesConfigMapError(Exception):
    pass
