import re
import socket
from typing import Any, Dict, Optional, Tuple

PROMPT = b"\nvde$ "
DATA_BEGIN = "0000 DATA END WITH"
DATA_END = "."
SUCCESS_CODE = 1000

STATUS_REGEX = re.compile(r"^(1\d{3})(?: (.*))?$")
PORT_REGEX = re.compile(r"^Port (\d+) untagged_vlan=(\d+) (IN)?ACTIVE")
ENDPOINT_REGEX = re.compile(r"^\s*-- endpoint ID \d+ module [^:]*: (.*?)(?: user=\S+ pid=\d+.*)?$")
VLAN_REGEX = re.compile(r"^VLAN (\d+)")
VLAN_PORT_REGEX = re.compile(r"^\s*-- Port (\d+) tagged=(\d)")

# Description given by the Kathara Network Plugin to the endpoints: `kathara` or `kathara <device>:eth<N>`
ENDPOINT_DESCRIPTION = "kathara"


class VdeManagement(object):
    """Client of the management socket of a VDE switch, used by the managed collision domains.

    A command is a line of text (e.g. `vlan/create 10`). The switch answers with an optional block of text and a
    status line, made of a numeric code (1000 on success, 1000 + errno on error) and a message.
    """
    __slots__ = ['socket_path', 'timeout', '_socket']

    def __init__(self, socket_path: str, timeout: float = 5.0) -> None:
        self.socket_path: str = socket_path
        self.timeout: float = timeout
        self._socket: Optional[socket.socket] = None

    def __enter__(self) -> 'VdeManagement':
        self.open()

        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def open(self) -> None:
        """Connect to the management socket.

        Returns:
            None

        Raises:
            OSError: If the socket cannot be opened.
        """
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            self._socket.settimeout(self.timeout)
            self._socket.connect(self.socket_path)
            # Skip the banner of the switch
            self._read_reply()
        except OSError:
            self.close()
            raise

    def close(self) -> None:
        """Close the connection to the management socket.

        Returns:
            None
        """
        if self._socket is not None:
            self._socket.close()
            self._socket = None

    def exec(self, command: str) -> Tuple[int, str, str]:
        """Run a command on the switch.

        Args:
            command (str): The command, on a single line.

        Returns:
            Tuple[int, str, str]: The status code of the command (1000 on success), its status message and
                the text it printed.

        Raises:
            ValueError: If the command is empty or spans several lines.
            ConnectionError: If the switch closes the connection or its answer has no status.
        """
        command = command.strip()
        if not command or '\n' in command or '\r' in command:
            raise ValueError("A command is a single line of text.")

        self._socket.sendall(f"{command}\n".encode('utf-8'))

        return self.parse_reply(self._read_reply())

    def _read_reply(self) -> str:
        """Read the text sent by the switch up to its next prompt.

        Returns:
            str: The text, without the prompt.

        Raises:
            ConnectionError: If the switch closes the connection.
        """
        data = b""
        while not data.endswith(PROMPT):
            chunk = self._socket.recv(4096)
            if not chunk:
                raise ConnectionError(f"Connection closed by the switch on `{self.socket_path}`.")
            data += chunk

        return data[:-len(PROMPT)].decode('utf-8', errors='replace')

    @staticmethod
    def parse_reply(reply: str) -> Tuple[int, str, str]:
        """Split the answer to a command.

        Args:
            reply (str): The text sent by the switch after a command.

        Returns:
            Tuple[int, str, str]: The status code, the status message and the printed text.

        Raises:
            ConnectionError: If there is no status in the answer.
        """
        code, message = None, ""
        lines = []
        in_data = False

        for line in reply.splitlines():
            if in_data:
                if line == DATA_END:
                    in_data = False
                else:
                    lines.append(line)
            elif line.startswith(DATA_BEGIN):
                in_data = True
            else:
                matches = STATUS_REGEX.match(line)
                if matches:
                    code, message = int(matches.group(1)), matches.group(2) or ""

        if code is None:
            raise ConnectionError(f"No status in the answer of the switch: `{reply}`.")

        return code, message, "\n".join(lines)

    @staticmethod
    def parse_ports(ports_output: str, vlans_output: str = "") -> Dict[int, Dict[str, Any]]:
        """Parse the port table and the VLAN table of a switch.

        Args:
            ports_output (str): The text printed by the `port/allprint` command.
            vlans_output (str): The text printed by the `vlan/allprint` command.

        Returns:
            Dict[int, Dict[str, Any]]: For each port number: `vlan` (the VLAN of the untagged frames),
                `tagged_vlans` (the VLANs exchanged tagged), `active` (True when something is plugged) and
                `endpoints` (what is plugged: `<device>:eth<N>` for the interface of a device).
        """
        ports = {}

        port = None
        for line in ports_output.splitlines():
            matches = PORT_REGEX.match(line)
            if matches:
                port = {'vlan': int(matches.group(2)), 'tagged_vlans': [], 'active': not matches.group(3),
                        'endpoints': []}
                ports[int(matches.group(1))] = port
                continue

            matches = ENDPOINT_REGEX.match(line)
            if matches and port is not None:
                description = matches.group(1).strip()
                if description.startswith(f"{ENDPOINT_DESCRIPTION} "):
                    description = description[len(ENDPOINT_DESCRIPTION) + 1:]
                port['endpoints'].append(description)

        vlan = None
        for line in vlans_output.splitlines():
            matches = VLAN_REGEX.match(line)
            if matches:
                vlan = int(matches.group(1))
                continue

            matches = VLAN_PORT_REGEX.match(line)
            if matches and vlan is not None and int(matches.group(1)) in ports and matches.group(2) == "1":
                ports[int(matches.group(1))]['tagged_vlans'].append(vlan)

        return ports
