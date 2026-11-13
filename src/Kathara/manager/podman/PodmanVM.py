import base64
import json
import shlex
import shutil
import subprocess
from typing import List

from ...exceptions import PodmanPluginError

ARCHITECTURES = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}


class PodmanVM:
    """The `podman machine` VM where Podman runs containers on macOS.

    On macOS the Podman engine, netavark and the Kathara network plugin live inside this VM, while Kathara
    runs on the Mac and talks to the engine through the machine API socket. This class only knows how to
    work inside the VM (run commands, read and write files, install archives); what to install is decided
    by the caller.
    """
    __slots__ = ['podman', 'name', 'socket_path']

    def __init__(self, podman: str, name: str, socket_path: str) -> None:
        self.podman: str = podman
        self.name: str = name
        self.socket_path: str = socket_path

    @classmethod
    def default(cls) -> "PodmanVM":
        """Return the default `podman machine` VM, checking that it can be used by Kathara.

        Returns:
            PodmanVM: The default machine.

        Raises:
            PodmanPluginError: If Podman is not installed, no machine exists, or the machine is not running
                or not rootless.
        """
        podman = shutil.which("podman")
        if podman is None:
            raise PodmanPluginError("Podman is not installed: install Podman 5 for macOS from https://podman.io.")

        try:
            result = subprocess.run([podman, "machine", "inspect"], capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            raise PodmanPluginError("`podman machine inspect` did not answer: check the Podman installation.")
        if result.returncode != 0:
            raise PodmanPluginError(
                f"No podman machine found ({result.stderr.strip()}): create it with `podman machine init`."
            )

        try:
            machine = json.loads(result.stdout)[0]
            name = machine["Name"]
            state = machine["State"]
            rootful = machine["Rootful"]
            socket_path = machine["ConnectionInfo"]["PodmanSocket"]["Path"]
        except (ValueError, IndexError, KeyError, TypeError):
            raise PodmanPluginError("Cannot read the output of `podman machine inspect`.")

        if state != "running":
            raise PodmanPluginError(
                f"The podman machine `{name}` is not running: start it with `podman machine start`."
            )
        if rootful:
            raise PodmanPluginError(
                f"The podman machine `{name}` is rootful, but Kathara needs a rootless one: "
                f"run `podman machine set --rootful=false {name}` and restart it."
            )

        return cls(podman, name, socket_path)

    @property
    def socket_url(self) -> str:
        """Return the URL of the machine API socket on the Mac.

        Returns:
            str: A `unix://` URL.
        """
        return f"unix://{self.socket_path}"

    @staticmethod
    def normalize_arch(raw: str) -> str:
        """Convert a `uname -m` value to the format of `utils.get_architecture()`.

        Args:
            raw (str): The output of `uname -m`.

        Returns:
            str: `amd64`, `arm64`, or the raw value for other architectures.
        """
        raw = raw.strip().lower()
        return ARCHITECTURES.get(raw, raw)

    def run(self, script: str, timeout: int = 300) -> subprocess.CompletedProcess:
        """Run a bash script inside the machine.

        The script travels base64-encoded as the remote command, so it needs no quoting.

        Args:
            script (str): The bash script to run.
            timeout (int): Seconds to wait before giving up.

        Returns:
            subprocess.CompletedProcess: The result, with `stdout` and `stderr` as text.

        Raises:
            PodmanPluginError: If the script does not finish within `timeout` seconds.
        """
        encoded = base64.b64encode(script.encode()).decode()
        command = f"echo {encoded} | base64 -d | bash"
        try:
            return subprocess.run([self.podman, "machine", "ssh", self.name, command],
                                  capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            raise PodmanPluginError(f"A command in the podman machine `{self.name}` did not finish in {timeout}s.")

    def run_checked(self, script: str, what: str, timeout: int = 300) -> subprocess.CompletedProcess:
        """Run a bash script inside the machine and fail if it does not succeed.

        Args:
            script (str): The bash script to run.
            what (str): What the script does, for the error message (e.g. "install the network plugin").
            timeout (int): Seconds to wait before giving up.

        Returns:
            subprocess.CompletedProcess: The result, with `stdout` and `stderr` as text.

        Raises:
            PodmanPluginError: If the script fails or does not finish within `timeout` seconds.
        """
        result = self.run(script, timeout)
        if result.returncode != 0:
            raise PodmanPluginError(f"Cannot {what} in the podman machine `{self.name}`: {result.stderr.strip()}")
        return result

    def query(self, commands: List[str], timeout: int = 30) -> List[str]:
        """Run several read-only commands in a single round trip and return one line of output for each.

        A command that fails or prints nothing yields an empty string, and multi-line output is joined on a
        single line, so the result always has exactly one element per command.

        Args:
            commands (List[str]): The commands to run, in order.
            timeout (int): Seconds to wait before giving up.

        Returns:
            List[str]: The output of each command, in the same order.

        Raises:
            PodmanPluginError: If the round trip itself fails.
        """
        script = "\n".join(f"{{ {command}\n}} 2>/dev/null | tr -d '\\n'; echo" for command in commands)
        result = self.run_checked(script, "read the configuration", timeout)
        lines = result.stdout.split("\n")
        return [lines[i] if i < len(lines) else "" for i in range(len(commands))]

    def write_file(self, path: str, content: str) -> None:
        """Write a text file inside the machine, atomically (a temporary file renamed over the target).

        Args:
            path (str): Absolute path of the file inside the machine.
            content (str): The text to write.

        Raises:
            PodmanPluginError: If the file cannot be written.
        """
        q = shlex.quote
        tmp = path + ".tmp"
        self.run_checked(" && ".join([
            f"mkdir -p -- \"$(dirname -- {q(path)})\"",
            f"printf %s {q(content)} > {q(tmp)}",
            f"mv -f -- {q(tmp)} {q(path)}",
        ]), f"write `{path}`")

    def install_archive(self, url: str, sha256: str, dest: str, top_dir: str) -> None:
        """Download a .tar.gz inside the machine, verify it and install its top directory at `dest`.

        The new directory replaces the old one with renames, so an interrupted update never leaves a
        half-installed copy.

        Args:
            url (str): URL of the archive.
            sha256 (str): Expected SHA-256 of the archive.
            dest (str): Absolute path, inside the machine, where the directory is installed.
            top_dir (str): Name of the top-level directory inside the archive.

        Raises:
            PodmanPluginError: If the download, the checksum or the installation fail.
        """
        q = shlex.quote
        work, old = dest + ".download", dest + ".old"
        self.run_checked(" && ".join([
            f"rm -rf -- {q(work)} {q(old)}",
            f"mkdir -p -- {q(work)}",
            f"cd -- {q(work)}",
            f"curl -fsSL -o bundle.tar.gz {q(url)}",
            f"echo {q(sha256 + '  bundle.tar.gz')} | sha256sum -c --quiet -",
            "tar -xzf bundle.tar.gz",
            f"{{ [ ! -e {q(dest)} ] || mv -- {q(dest)} {q(old)}; }}",
            f"mv -- {q(top_dir)} {q(dest)}",
            "cd /",
            f"rm -rf -- {q(old)} {q(work)}",
        ]), f"install `{url}`")

    def restart_podman(self) -> None:
        """Restart the user Podman API service in the machine, if it is running, so it reloads its configuration.

        Raises:
            PodmanPluginError: If the service cannot be restarted.
        """
        self.run_checked("systemctl --user try-restart podman.service", "restart the Podman service", timeout=60)