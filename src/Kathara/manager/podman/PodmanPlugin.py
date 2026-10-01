import hashlib
import json
import logging
import os
import shutil
import sys
import tarfile
import tempfile
from typing import Optional
import subprocess
from ... import utils
from ...exceptions import PodmanPluginError
from ...setting.Setting import Setting
import requests

PLUGIN_NAME = "katharanp_vde"                  # = driver name = executable name
PLUGIN_VERSION = "v0.1.4"                       # plugin release this Kathará version expects
SUPPORTED_ARCHITECTURES = {"amd64", "arm64"}    # architectures with a published plugin bundle
RELEASE_URL = ("https://github.com/oligiochi/katharanp-netavark/releases/download/" "{version}/katharanp-netavark-{version}-linux-{arch}.tar.gz")

class PodmanPlugin(object):
    """Class responsible for interacting with Podman Plugins."""
    __slots__ = ['install_dir']

    def __init__(self) -> None:
        data_home = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
        self.install_dir: str = os.path.join(data_home, "kathara", "katharanp")
        
    def check_and_download_plugin(self) -> None:
        """Check the Kathara network plugin and install or update it, if needed.

        Returns:
            None

        Raises:
            PodmanPluginError: If Podman is reached through a remote connection, or if the plugin
                cannot be installed or the Podman service cannot be restarted.
        """
        
        if sys.platform != "linux":
            raise PodmanPluginError(
                "The Podman backend is only supported on Linux hosts: on macOS and Windows Podman runs "
                "containers in a `podman machine` VM, where the Kathara network plugin cannot be installed yet."
            )
        
        socket_url = Setting.get_instance().api_socket_url
        if socket_url and not socket_url.startswith("unix://"):
            raise PodmanPluginError(
                "The Kathara network plugin cannot be installed on a remote Podman connection "
                f"(`{socket_url}`): install it on the remote host."
            )

        changed = False
        if self._installed_version() != PLUGIN_VERSION:
            self._download_and_install()
            changed = True
        changed = self._ensure_plugin_dir_configured() or changed
        if changed:
            self._restart_podman_service()
            
    def _installed_version(self) -> Optional[str]:
        """Return the version of the installed plugin, or None if it is missing or broken.

        Returns:
            Optional[str]: The version reported by `katharanp_vde info`, or None.
        """
        plugin = os.path.join(self.install_dir, "bin", PLUGIN_NAME)
        try:
            result = subprocess.run([plugin, "info"], capture_output=True, timeout=10)
            return json.loads(result.stdout)["version"] if result.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError):
            return None
    def _download_and_install(self) -> None:
        """Download the plugin bundle for this architecture, verify it, and replace the current installation.

        Raises:
            PodmanPluginError: If the architecture is not supported, the download fails or the checksum
                does not match.
        """
        arch = utils.get_architecture()
        if arch not in SUPPORTED_ARCHITECTURES:
            raise PodmanPluginError(f"The Kathara network plugin is not available for the `{arch}` architecture.")

        url = RELEASE_URL.format(version=PLUGIN_VERSION, arch=arch)
        logging.info(f"Installing Kathara network plugin {PLUGIN_VERSION}...")

        parent = os.path.dirname(self.install_dir)
        os.makedirs(parent, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as tmp:
            bundle = os.path.join(tmp, "bundle.tar.gz")
            self._download(url, bundle)
            expected = self._download_text(url + ".sha256").split()[0]
            if self._sha256(bundle) != expected:
                raise PodmanPluginError(f"Checksum mismatch for `{url}`: the download may be corrupted.")

            with tarfile.open(bundle) as archive:
                archive.extractall(tmp, filter="data")

            # Swap the new installation in with renames (atomic on the same filesystem), so an interrupted
            # update never leaves a half-installed plugin.
            old = self.install_dir + ".old"
            shutil.rmtree(old, ignore_errors=True)
            if os.path.exists(self.install_dir):
                os.rename(self.install_dir, old)
            os.rename(os.path.join(tmp, "katharanp"), self.install_dir)
            shutil.rmtree(old, ignore_errors=True)

        logging.info("Kathara network plugin installed successfully!")

    @staticmethod
    def _download(url: str, destination: str) -> None:
        try:
            with requests.get(url, stream=True, timeout=30) as response:
                response.raise_for_status()
                with open(destination, "wb") as f:
                    for chunk in response.iter_content(chunk_size=65536):
                        f.write(chunk)
        except requests.RequestException as e:
            raise PodmanPluginError(f"Cannot download the Kathara network plugin from `{url}`: {e}")

    @staticmethod
    def _download_text(url: str) -> str:
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            raise PodmanPluginError(f"Cannot download `{url}`: {e}")

    @staticmethod
    def _sha256(path: str) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(65536), b""):
                digest.update(block)
        return digest.hexdigest()
            
        
    def _ensure_plugin_dir_configured(self) -> bool:
        """Register the plugin directory in the user Podman configuration (a containers.conf drop-in).

        Returns:
            bool: True if the configuration was changed (the Podman service must be restarted to see it).
        """
        config_home = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
        dropin = os.path.join(config_home, "containers", "containers.conf.d", "kathara.conf")
        plugin_dir = os.path.join(self.install_dir, "bin")
        # `{append=true}` adds the directory to the plugin directories instead of replacing them,
        # so plugins configured elsewhere (system or user) keep working.
        content = (
            "# Managed by Kathara: directory of the Kathara netavark network plugin.\n"
            "[network]\n"
            f'netavark_plugin_dirs = ["{plugin_dir}", {{append=true}}]\n'
        )

        try:
            with open(dropin) as f:
                if f.read() == content:
                    return False
        except FileNotFoundError:
            pass

        logging.debug(f"Writing Podman configuration `{dropin}`...")
        os.makedirs(os.path.dirname(dropin), exist_ok=True)
        tmp = dropin + ".tmp"
        with open(tmp, "w") as f:
            f.write(content)
        os.replace(tmp, dropin)
        return True

    @staticmethod
    def _restart_podman_service() -> None:
        """Restart the user Podman API service, so that it reloads the configuration and sees the plugin.

        Only a running service is restarted (`try-restart`): if it is not running, the next request
        through the socket starts it with the new configuration anyway.

        Raises:
            PodmanPluginError: If the service cannot be restarted.
        """
        systemctl = shutil.which("systemctl")
        if systemctl is None:
            raise PodmanPluginError(
                "Cannot restart the Podman service to load the Kathara network plugin: systemctl not found. "
                "Restart the Podman API service manually and run Kathara again."
            )

        logging.debug("Restarting the Podman API service...")
        result = subprocess.run([systemctl, "--user", "try-restart", "podman.service"],
                                capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise PodmanPluginError(
                f"Cannot restart the Podman service to load the Kathara network plugin: {result.stderr.strip()}"
            )
    