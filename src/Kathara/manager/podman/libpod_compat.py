import json
import struct
import urllib.parse
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
import shlex
from podman import PodmanClient
from podman import api as podman_api
from podman.api.output_utils import demux_output
from podman.domain.containers import Container
from podman.domain.networks import Network
from podman.errors import APIError

SYSCTL_OPTION_PREFIX = "sysctl."


class LibpodCompat(object):
    """Compatibility layer over the libpod REST API.

    Contains only the operations that podman-py does not expose, or exposes incompletely.
    Every method should be removed as soon as podman-py supports it natively.
    Transport (connection, pooling, API versioning) is delegated to podman-py's `APIClient`.
    """
    __slots__ = ['_api']

    def __init__(self, podman_client: PodmanClient) -> None:
        """Create the compatibility layer.

        Args:
            podman_client (podman.PodmanClient): The podman-py client whose API transport is reused.
        """
        self._api = podman_client.api

    def exec_create(self, container_id: str, cmd: Union[str, List[str]], stdout: bool = True, stderr: bool = True,
                    stdin: bool = False, tty: bool = False, privileged: bool = False, user: str = '',
                    environment: Optional[Union[Dict[str, str], List[str]]] = None,
                    workdir: Optional[str] = None) -> str:
        """Create an exec instance on a container.

        Args:
            container_id (str): The ID or name of the container.
            cmd (Union[str, List[str]]): The command to execute.
            stdout (bool): Attach to stdout.
            stderr (bool): Attach to stderr.
            stdin (bool): Attach to stdin.
            tty (bool): Allocate a pseudo-TTY.
            privileged (bool): Run the command in privileged mode.
            user (str): The user that runs the command.
            environment (Optional[Union[Dict[str, str], List[str]]]): Environment variables.
            workdir (Optional[str]): The working directory of the command.

        Returns:
            str: The ID of the exec instance.

        Raises:
            APIError: If the Podman APIs return an error.
        """
        if isinstance(environment, dict):
            environment = [f"{k}={v}" for k, v in environment.items()]

        payload = {
            "AttachStdin": stdin, 
            "AttachStdout": stdout, 
            "AttachStderr": stderr,
            "Tty": tty, 
            "Cmd": cmd if isinstance(cmd, list) else shlex.split(cmd), 
            "Privileged": privileged,
            "Env": environment, "WorkingDir": workdir,
        }
        if user:
            payload["User"] = user

        resp = self._api.post(
            f"/containers/{container_id}/exec",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload),
        )
        resp.raise_for_status()
        return resp.json()["Id"]

    def exec_start(self, exec_id: str, tty: bool = False, detach: bool = False, stream: bool = False,
                   demux: bool = False) -> Union[bytes, Tuple[Optional[bytes], Optional[bytes]], Generator]:
        """Start a previously created exec instance.

        Args:
            exec_id (str): The ID of the exec instance.
            tty (bool): Whether the exec instance has a pseudo-TTY.
            detach (bool): Start the exec instance in detached mode.
            stream (bool): Return a generator over the output frames (ignored if detach is True).
            demux (bool): Separate stdout and stderr.

        Returns:
            Union[bytes, Tuple[Optional[bytes], Optional[bytes]], Generator]:
                - stream=True: a generator of frames, or of (stdout, stderr) tuples if demux=True.
                - stream=False, demux=True: a (stdout, stderr) tuple.
                - otherwise: the output as bytes (stdout and stderr in arrival order, without
                  multiplexing headers).

        Raises:
            APIError: If the Podman APIs return an error.
        """
        stream = stream and not detach

        resp = self._api.post(
            f"/exec/{exec_id}/start",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"Detach": detach, "Tty": tty}),
            stream=stream,
        )
        resp.raise_for_status()

        if stream:
            return podman_api.stream_frames(resp, demux=demux)
        if demux:
            return demux_output(resp.content)
        return resp.content if tty else self._join_frames(resp.content)

    def exec_start_hijack(self, exec_id: str, tty: bool = True) -> Any:
        """Start an exec instance in interactive mode and hijack the underlying raw socket.

        The caller owns the returned socket and must close it: each hijacked socket permanently
        consumes a connection of the urllib3 pool.

        Args:
            exec_id (str): The ID of the exec instance.
            tty (bool): Whether the exec instance has a pseudo-TTY.

        Returns:
            Any: The raw, blocking socket connected to the exec instance.

        Raises:
            APIError: If the Podman APIs do not switch protocols (HTTP 101).
        """
        resp = self._api.post(
            f"/exec/{exec_id}/start",
            headers={
                "Content-Type": "application/json",
                "Connection": "Upgrade", "Upgrade": "tcp",
            },
            data=json.dumps({"Detach": False, "Tty": tty}),
            stream=True,
        )
        if resp.status_code != 101:
            resp.raise_for_status()
            raise APIError(f"Exec `{exec_id}`: expected HTTP 101 Switching Protocols, got {resp.status_code}.",
                           response=resp)

        sock = resp.raw.connection.sock
        sock._hijacked_response = resp  # Prevents urllib3 from reclaiming the connection
        sock.settimeout(None)  # Interactive session: drop the HTTP read timeout inherited from urllib3
        return sock

    def exec_inspect(self, exec_id: str) -> Dict[str, Any]:
        """Return the current state of an exec instance.

        Args:
            exec_id (str): The ID of the exec instance.

        Returns:
            Dict[str, Any]: The exec instance state, including `ExitCode` and `Running`.

        Raises:
            APIError: If the Podman APIs return an error.
        """
        resp = self._api.get(f"/exec/{exec_id}/json")
        resp.raise_for_status()
        return resp.json()

    def exec_resize(self, exec_id: str, cols: int, rows: int) -> None:
        """Resize the pseudo-TTY of a running exec instance.

        Args:
            exec_id (str): The ID of the exec instance.
            cols (int): The number of columns.
            rows (int): The number of rows.

        Raises:
            APIError: If the Podman APIs return an error.
        """
        resp = self._api.post(f"/exec/{exec_id}/resize", params={"h": rows, "w": cols})
        resp.raise_for_status()

    @staticmethod
    def _join_frames(content: bytes) -> bytes:
        """Strip the 8-byte multiplexing headers, keeping stdout/stderr in arrival order.

        Args:
            content (bytes): The multiplexed output of a non-TTY exec instance.

        Returns:
            bytes: The output without multiplexing headers.
        """
        out, i = bytearray(), 0
        while i + 8 <= len(content):
            size = struct.unpack(">I", content[i + 4:i + 8])[0]
            out += content[i + 8:i + 8 + size]
            i += 8 + size
        return bytes(out)

    @staticmethod
    def sysctl_options(sysctls: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """Convert sysctls into the per-network options understood by the Kathará network plugin.

        Args:
            sysctls (Optional[Dict[str, Any]]): Sysctls as `key: value`, e.g. `{"net.ipv4.conf.eth1.rp_filter": 0}`.

        Returns:
            Dict[str, str]: The options with the `sysctl.` prefix, or an empty dict if there are no sysctls.
        """
        if not sysctls:
            return {}
        return {f"{SYSCTL_OPTION_PREFIX}{k}": str(v) for k, v in sysctls.items()}

    def network_connect(self, network: Union[str, Network], container: Union[str, Container],
                        interface_name: str, mac_address: Optional[str] = None,
                        sysctls: Optional[Dict[str, Any]] = None,
                        aliases: Optional[List[str]] = None) -> None:
        """Connect a running container to a network, choosing interface name, MAC address and sysctls.

        Args:
            network (Union[str, Network]): The network object or its name.
            container (Union[str, Container]): The container object or its ID.
            interface_name (str): The name of the interface inside the container (e.g. `eth1`).
            mac_address (Optional[str]): A static MAC address for the interface.
            sysctls (Optional[Dict[str, Any]]): Sysctls to apply to the interface, applied by the network plugin.
            aliases (Optional[List[str]]): Network aliases for the attachment, returned back by inspect
                in `NetworkSettings.Networks[<network>].Aliases`.

        Raises:
            APIError: If the Podman APIs return an error, including when the network plugin
                fails to apply a sysctl (e.g. a non-existent key).
        """
        network_name = network.name if isinstance(network, Network) else network
        container_id = container.id if isinstance(container, Container) else container

        body = {"container": container_id, "interface_name": interface_name}
        if mac_address:
            body["static_mac"] = mac_address
        options = self.sysctl_options(sysctls)
        if options:
            body["options"] = options
        if aliases:
            body["aliases"] = aliases

        resp = self._api.post(
            f"/networks/{network_name}/connect",
            headers={"Content-Type": "application/json"},
            data=json.dumps(body),
        )
        resp.raise_for_status()
    
    def inspect_remote_manifest(self, name: str) -> Dict[str, Any]:
        """Query the registry for the manifest of a tagged image reference, without pulling it.

        The compat `/distribution/{name}/json` endpoint and podman-py's `get_registry_data` never
        leave local storage; only this libpod endpoint actually reaches the registry.

        Args:
            name (str): The fully qualified image reference to inspect
                (e.g. `docker.io/kathara/base:latest`).

        Returns:
            Dict[str, Any]: The manifest, or manifest index, as returned by the registry.

        Raises:
            APIError: If the registry lookup fails (image or tag not found, registry unreachable,
                rate limited, ...).
        """
        encoded_name = urllib.parse.quote(name, safe="/:")
        resp = self._api.get(f"/manifests/{encoded_name}/json", params={"tlsVerify": "true"})
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def container_status(container: Container) -> str:
        """Return the status of a container, whatever format its attributes come from.

        podman-py's `Container.status` assumes the inspect format (`State` is a dict), but containers
        obtained from `containers.list()` carry `State` as a plain string, which makes it raise a TypeError.

        Args:
            container (Container): A podman-py container.

        Returns:
            str: The container status (e.g. `running`), or `unknown` if not available.
        """
        state = container.attrs.get("State")
        if isinstance(state, dict):
            return state.get("Status", "unknown")
        return state or "unknown"