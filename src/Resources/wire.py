from .setting.Setting import Setting
from .manager.ManagerProxy import ManagerProxy
from .model.Lab import Lab
from . import utils
from socket import socket
from subprocess import Popen
import logging
import sys


def portnum(i):
    try:
        base_port = int(Setting.get_instance().wire_ports.strip().split("-")[0])
        return base_port + i
    except:
        return 5000 + i


def portmax():
    try:
        return int(Setting.get_instance().wire_ports.strip().split("-")[1])
    except:
        return 5020


def get_snoop():
    client = ManagerProxy.get_instance().manager.client
    snoop_name = Setting.get_instance().wire_snoop
    try:
        return client.containers.get(snoop_name)
    except:
        return None


def stop_snoop():
    snoop = get_snoop()
    if snoop is not None:
        snoop.kill()


def start_snoop():
    snoop = get_snoop()
    if snoop is not None:
        return
    client = ManagerProxy.get_instance().manager.client
    snoop_image = Setting.get_instance().wire_image
    snoop_name = Setting.get_instance().wire_snoop
    base_port = portnum(0)
    end_port = portmax()
    ports = {}
    for i in range(end_port - base_port + 1):
        ports["{}/tcp".format(5000 + i)] = base_port + i
    args = {
        "name": snoop_name,
        "ports": ports,
        "sysctls": {
            "net.ipv6.conf.all.disable_ipv6": 1,
            "net.ipv6.conf.default.disable_ipv6": 1,
            "net.ipv4.conf.all.send_redirects": 0,
        },
        "auto_remove": True,
        "detach": True,
        "labels": {
            "lab_hash": Lab(utils.get_vlab_temp_path()).folder_hash,
            "name": "wire_snoop",
            "app": "kathara",
            "user": utils.get_current_user_name(),
            "shell": "/bin/sh",
        },
    }
    res = client.containers.run(snoop_image, **args)
    logs = res.logs(stream=True, stdout=True)


def connect_snoop(link_name, network):
    snoop = get_snoop()
    if snoop is None:
        logging.critical("Missing snoop VM")
        exit(1)
    network.connect(Setting.get_instance().wire_snoop)


def snoop_port(name):
    docker_link = ManagerProxy.get_instance().manager.docker_link
    try:
        network = docker_link.get_links_by_filters(link_name=name).pop()
    except:
        logging.error("Network {} not found".format(name))
        sys.exit(1)
    s = socket()
    s.connect(("", portnum(0)))
    s.send(("DUMP {}\n".format(name)).encode())
    res = s.recv(1024).strip().split()
    if res[0] == b"NEW":
        connect_snoop(name, network)
    return portnum(int(res[-1])) - 5000


def capture(nets):
    ports = [snoop_port(name) for name in nets]
    cmd = [Setting.get_instance().wire_command]
    for port in ports:
        cmd.append("-i")
        cmd.append("TCP@[127.0.0.1]:{}".format(port))
    cmd.append("-k")
    Popen(cmd)
