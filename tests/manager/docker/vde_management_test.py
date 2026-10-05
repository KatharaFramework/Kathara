import os
import socket
import sys
import tempfile
import threading

import pytest

sys.path.insert(0, './')

from src.Kathara.manager.docker.VdeManagement import VdeManagement, PROMPT, SUCCESS_CODE

BANNER = b"VDE switch V.2.3.3\n(C) Virtual Square Team (coord. R. Davoli) 2005,2006,2007 - GPLv2\n"

PORTS_OUTPUT = """Port 0001 untagged_vlan=0000 ACTIVE - NOT Unnamed Allocatable
 Current User: root Access Control: (User: NONE - Group: NONE)
  -- endpoint ID 0003 module unix prog   : kathara r1:eth0 user=0 pid=64086
Port 0002 untagged_vlan=0010 ACTIVE - NOT Unnamed Allocatable
 Current User: root Access Control: (User: NONE - Group: NONE)
  -- endpoint ID 0008 module unix prog   : kathara pc2:eth0 user=0 pid=64086
Port 0003 untagged_vlan=0020 INACTIVE - NOT Unnamed Allocatable
 Current User: NONE Access Control: (User: NONE - Group: NONE)
Port 0005 untagged_vlan=0000 ACTIVE - Unnamed Allocatable
 Current User: root Access Control: (User: NONE - Group: NONE)
  -- endpoint ID 0012 module unix prog   : kathara user=0 pid=64086
  -- endpoint ID 0014 module unix prog   : vde_ext: eth1 user=0 pid=70000"""

VLANS_OUTPUT = """VLAN 0000
 -- Port 0001 tagged=0 active=1 status=Forwarding
 -- Port 0005 tagged=0 active=1 status=Forwarding
VLAN 0010
 -- Port 0001 tagged=1 active=1 status=Forwarding
 -- Port 0002 tagged=0 active=1 status=Forwarding
VLAN 0020
 -- Port 0001 tagged=1 active=1 status=Forwarding
 -- Port 0003 tagged=0 active=0 status=Forwarding"""

REPLIES = {
    "vlan/create 10": b"1000 Success\n",
    "vlan/create 20": b"1017 File exists\n",
    "port/allprint": b"0000 DATA END WITH '.'\n" + PORTS_OUTPUT.encode() + b"\n.\n1000 Success\n",
    "vlan/allprint": b"0000 DATA END WITH '.'\n" + VLANS_OUTPUT.encode() + b"\n.\n1000 Success\n",
}


@pytest.fixture()
def management_socket():
    """A management socket served by a fake switch, which answers to the commands of REPLIES."""
    directory = tempfile.mkdtemp()
    socket_path = os.path.join(directory, "mgmt")
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(socket_path)
    server.listen(1)

    def serve():
        while True:
            try:
                connection, _ = server.accept()
            except OSError:
                return

            with connection:
                connection.sendall(BANNER + PROMPT)
                buffer = b""
                while True:
                    data = connection.recv(4096)
                    if not data:
                        break
                    buffer += data
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        command = line.decode()
                        if command == "hangup":
                            connection.close()
                            return
                        # The replies are sent in two parts, as the switch does not send them in one packet
                        reply = REPLIES.get(command, b"1038 Function not implemented\n") + PROMPT
                        connection.sendall(reply[:7])
                        connection.sendall(reply[7:])

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    yield socket_path

    server.close()
    os.remove(socket_path)
    os.rmdir(directory)


#
# TEST: exec
#
def test_exec_success(management_socket):
    with VdeManagement(management_socket) as management:
        assert management.exec("vlan/create 10") == (SUCCESS_CODE, "Success", "")


def test_exec_error(management_socket):
    with VdeManagement(management_socket) as management:
        assert management.exec("vlan/create 20") == (1017, "File exists", "")
        assert management.exec("nosuch/command") == (1038, "Function not implemented", "")


def test_exec_output(management_socket):
    with VdeManagement(management_socket) as management:
        code, message, output = management.exec("  port/allprint  ")

    assert code == SUCCESS_CODE
    assert message == "Success"
    assert output == PORTS_OUTPUT


def test_exec_several_commands(management_socket):
    with VdeManagement(management_socket) as management:
        assert management.exec("vlan/create 10")[0] == SUCCESS_CODE
        assert management.exec("vlan/allprint")[2] == VLANS_OUTPUT


@pytest.mark.parametrize("command", ["", "   ", "vlan/create 10\nshutdown", "vlan/create 10\rshutdown"])
def test_exec_invalid_command(management_socket, command):
    with VdeManagement(management_socket) as management:
        with pytest.raises(ValueError):
            management.exec(command)


def test_exec_connection_closed(management_socket):
    with VdeManagement(management_socket) as management:
        with pytest.raises(ConnectionError):
            management.exec("hangup")


def test_open_no_socket():
    management = VdeManagement("/nonexistent/mgmt")
    with pytest.raises(OSError):
        management.open()

    management.close()


#
# TEST: parse_reply
#
def test_parse_reply_no_status():
    with pytest.raises(ConnectionError):
        VdeManagement.parse_reply("garbage\n")


def test_parse_reply_status_in_data():
    reply = "0000 DATA END WITH '.'\n1017 is not a status here\n.\n1000 Success\n"
    assert VdeManagement.parse_reply(reply) == (SUCCESS_CODE, "Success", "1017 is not a status here")


#
# TEST: parse_ports
#
def test_parse_ports():
    assert VdeManagement.parse_ports(PORTS_OUTPUT, VLANS_OUTPUT) == {
        1: {'vlan': 0, 'tagged_vlans': [10, 20], 'active': True, 'endpoints': ['r1:eth0']},
        2: {'vlan': 10, 'tagged_vlans': [], 'active': True, 'endpoints': ['pc2:eth0']},
        3: {'vlan': 20, 'tagged_vlans': [], 'active': False, 'endpoints': []},
        5: {'vlan': 0, 'tagged_vlans': [], 'active': True, 'endpoints': ['kathara', 'vde_ext: eth1']},
    }


def test_parse_ports_empty():
    assert VdeManagement.parse_ports("", "") == {}
    assert VdeManagement.parse_ports(PORTS_OUTPUT)[1]['tagged_vlans'] == []
