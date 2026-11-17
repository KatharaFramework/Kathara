from typing import NoReturn

from ...exceptions import NotSupportedError


def not_supported_in_rootless(feature: str) -> NoReturn:
    """Raise a `NotSupportedError` for a feature unsupported by the rootless Podman backend.

    The Podman backend only runs rootless: each user gets their own isolated Podman engine, with no
    privileges on the host and no visibility into the resources of other users. Because of this, some
    Kathará features that require host-level privileges or a single engine shared across users (e.g.
    attaching external interfaces, sharing collision domains between users, or inspecting/wiping the
    resources of other users) cannot be implemented on this backend. Rather than silently degrading or
    falling back to a different behavior, callers must invoke this function to fail immediately, before
    any network or container is created or removed.

    Args:
        feature (str): The name of the unsupported feature.

    Returns:
        NoReturn: This function never returns, it always raises.

    Raises:
        NotSupportedError: Always raised, stating that `feature` is not supported by the rootless
            Podman backend.
    """
    raise NotSupportedError(
        f"{feature} is not supported by the Podman backend: rootless Podman runs one isolated engine per "
        f"user. Use the Docker backend if you need it."
    )
