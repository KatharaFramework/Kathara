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
    def __init__(self, message: str) -> None:
        super().__init__(f"Settings file is not valid: {message} Fix it or delete it before launching.")


class SettingsNotFoundError(Exception):
    def __init__(self, path: str) -> None:
        super().__init__(f"Settings file not found in path `{path}`.")


class DockerDaemonConnectionError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"Cannot connect to Docker Daemon: {message}")


class NotSupportedError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(f"Not Supported: {message}")


# OS Exceptions
class PrivilegeError(Exception):
    pass


class InterfaceNotFoundError(Exception):
    pass


class HostArchitectureError(Exception):
    def __init__(self, architecture: str) -> None:
        super().__init__(f"Not implemented for host architecture `{architecture}`.")


# Lab Exceptions
class LabAlreadyExistsError(Exception):
    pass


class LabNotFoundError(Exception):
    pass


class EmptyLabError(Exception):
    def __init__(self) -> None:
        super().__init__("No devices in the current network scenario.")


class MachineDependencyError(Exception):
    pass


# Machine Exceptions
class MountDeniedError(Exception):
    pass


class MachineAlreadyExistsError(Exception):
    def __init__(self, machine_name: str) -> None:
        super().__init__(f"Device with name `{machine_name}` already exists.")


class NonSequentialMachineInterfaceError(Exception):
    def __init__(self, iface_num: int, machine_name: str) -> None:
        super().__init__(f"Interface `{iface_num}` missing on device `{machine_name}`.")


class MachineOptionError(Exception):
    pass


class MachineCollisionDomainError(Exception):
    pass


class MachineNotFoundError(Exception):
    pass


class MachineNotReadyError(Exception):
    def __init__(self, machine_name: str) -> None:
        super().__init__(f"Device `{machine_name}` is not ready.")


# Link Exceptions
class LinkNotFoundError(Exception):
    pass


class LinkAlreadyExistsError(Exception):
    pass


# Test Exceptions
class TestError(Exception):
    pass


class MachineSignatureNotFoundError(TestError):
    __slots__ = ['machine_name']

    def __init__(self, machine_name: str):
        self.machine_name: str = machine_name

    def __str__(self):
        return f"Signature for device `{self.machine_name}` not found!"


# Docker Exceptions
class InvalidImageArchitectureError(ValueError):
    __slots__ = ['image_name', 'arch']

    def __init__(self, image_name: str, arch: str):
        self.image_name: str = image_name
        self.arch: str = arch

    def __str__(self):
        return f"Docker Image `{self.image_name}` is not compatible with your host architecture `{self.arch}`"


class DockerImageNotFoundError(Exception):
    def __init__(self, image_name: str) -> None:
        super().__init__(f"Docker Image `{image_name}` is not available neither on Docker Hub nor in local repository!")


class DockerPluginError(Exception):
    pass


# Kubernetes Exceptions
class KubernetesConfigMapError(Exception):
    pass
