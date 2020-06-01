from datetime import datetime

import docker
import os
import time
import sys
from requests.exceptions import ConnectionError as RequestsConnectionError
from terminaltables import DoubleTable

from .DockerImage import DockerImage
from .DockerLink import DockerLink
from .DockerMachine import DockerMachine
from .DockerPlugin import DockerPlugin
from ... import utils
from ...auth.PrivilegeHandler import PrivilegeHandler
from ...exceptions import DockerDaemonConnectionError
from ...foundation.manager.IManager import IManager
from ...model.Link import BRIDGE_LINK_NAME
from ...os.Networking import Networking
from bash import bash


def pywin_import_stub():
    """
    Stub module of pywintypes for Unix systems (so it won't raise any `module not found` exception).
    """
    import types
    pywintypes = types.ModuleType("pywintypes")
    pywintypes.error = RequestsConnectionError
    return pywintypes


def pywin_import_win():
    import pywintypes
    return pywintypes


def privileged(method):
    """
    Decorator function to execute Docker daemon with proper privileges.
    They are then dropped when method is executed.
    """

    def exec_with_privileges(*args, **kw):
        utils.exec_by_platform(PrivilegeHandler.get_instance().raise_privileges, lambda: None, lambda: None)
        result = method(*args, **kw)
        utils.exec_by_platform(PrivilegeHandler.get_instance().drop_privileges, lambda: None, lambda: None)

        return result

    return exec_with_privileges


def check_docker_status(method):
    """
    Decorator function to check if Docker daemon is running properly.
    """
    pywintypes = utils.exec_by_platform(pywin_import_stub, pywin_import_win, pywin_import_stub)

    @privileged
    def check_docker(*args, **kw):
        # Call the constructor first
        method(*args, **kw)

        # Client is initialized after constructor call
        client = args[0].client

        # Try to ping Docker, to see if it's running and raise an exception on failure
        try:
            client.ping()
        except RequestsConnectionError as e:
            raise DockerDaemonConnectionError("Can not connect to Docker Daemon. %s" % str(e))
        except pywintypes.error as e:
            raise DockerDaemonConnectionError("Can not connect to Docker Daemon. %s" % str(e))

    return check_docker


class DockerManager(IManager):
    __slots__ = ['docker_image', 'docker_machine', 'docker_link', 'client']

    @check_docker_status
    def __init__(self):
        self.client = docker.from_env(timeout=None)

        docker_plugin = DockerPlugin(self.client)
        docker_plugin.check_and_download_plugin()

        self.docker_image = DockerImage(self.client)

        self.docker_machine = DockerMachine(self, self.client, self.docker_image)
        self.docker_link = DockerLink(self.client, docker_plugin)

    @privileged
    def deploy_lab(self, lab, privileged_mode=False):
        # Deploy all lab links.
        self.docker_link.deploy_links(lab)

        # Deploy all lab machines.
        self.docker_machine.deploy_machines(lab, privileged_mode=privileged_mode)
        sys.setrecursionlimit(10000)
        # Avvia la creazione dei lab interni
        self.runNestedLab(lab)
        # Collega i domini specificati nel lab.int
        self.createDomain(lab)

    @privileged
    def update_lab(self, lab_diff):
        # Deploy new links (if present)
        for (_, link) in lab_diff.links.items():
            if link.name == BRIDGE_LINK_NAME:
                continue

            self.docker_link.create(link)

        # Update lab machines.
        for (_, machine) in lab_diff.machines.items():
            self.docker_machine.update(machine)

    @privileged
    def undeploy_lab(self, lab_hash, selected_machines=None):
        if len(selected_machines) == 0:
            list_container = self.client.containers.list()
            list_volume = self.getListVolume(list_container)
            self.docker_machine.undeploy(lab_hash,
                                         selected_machines=selected_machines
                                         )
            self.docker_link.undeploy(lab_hash)
            self.delListVolume(list_volume)
        else:
            dict_machine = self.checkListPath(selected_machines)
            selected_machines = dict_machine['Correct']
            invalid_machines = dict_machine['Invalid']
            client_master = self.client
            selected_machines = self.getFilterMachinePath(selected_machines)
            if len(invalid_machines) == 0:
                for machine in selected_machines:
                    self.client = self.getParentClient(machine)
                    container = self.getContainerByName(client_master, list(reversed(machine.split('.'))))
                    machine_id = self.getIdMachine(machine)
                    volume = self.getVolumeByName(machine_id)
                    self.docker_machine.undeploy(container.labels['lab_hash'],
                                                 selected_machines=machine.split('.')[0]
                                                 )
                    self.docker_link.undeploy(lab_hash)
                    self.client.volumes.get(volume).remove()
                    self.client = client_master
            else:
                print("Le seguenti macchine non esistono " + str(invalid_machines))

    @privileged
    def wipe(self, all_users=False):
        user_name = utils.get_current_user_name() if not all_users else None

        self.docker_machine.wipe(user=user_name)
        self.docker_link.wipe(user=user_name)

    @privileged
    def connect_tty(self, lab_hash, machine_name, shell, logs=False):
        if self.checkPath(machine_name):
            if self.getHostname() != "":
                machine_name += '.' + self.getHostname()[:-1]
            self.client = self.getParentClient(machine_name)
            self.docker_machine.connect(lab_hash=lab_hash,
                                        machine_name=machine_name,
                                        shell=shell,
                                        logs=logs
                                        )
        else:
            raise Exception('Invalid path')

    @privileged
    def exec(self, machine, command):
        return self.docker_machine.exec(machine.api_object,
                                        command=command
                                        )

    @privileged
    def copy_files(self, machine, path, tar_data):
        self.docker_machine.copy_files(machine.api_object,
                                       path=path,
                                       tar_data=tar_data
                                       )

    @privileged
    def get_lab_info(self, recursive, lab_hash=None, machine_name=None, all_users=False):
        user_name = utils.get_current_user_name() if not all_users else None
        if not recursive:
            machines = self.docker_machine.get_machines_by_filters(lab_hash=lab_hash,
                                                                   machine_name=machine_name,
                                                                   user=user_name
                                                                   )
        else:
            machines = self.docker_machine.get_machines_by_filters_rec(lab_hash=lab_hash,
                                                                       machine_name=machine_name,
                                                                       user=user_name
                                                                       )
        if not machines:
            if not lab_hash:
                raise Exception("No machines running.")
            else:
                raise Exception("Lab is not started.")

        machines = sorted(machines, key=lambda x: x.name)

        machine_streams = {}

        for machine in machines:
            machine_streams[machine] = machine.stats(stream=True, decode=True)

        table_header = ["LAB HASH", "USER", "MACHINE NAME", "STATUS", "CPU %", "MEM USAGE / LIMIT", "MEM %", "NET I/O"]
        stats_table = DoubleTable([])
        stats_table.inner_row_border = True

        while True:
            machines_data = [
                table_header
            ]

            for (machine, machine_stats) in machine_streams.items():
                real_name = machine.labels['name']
                if recursive:
                    path = machine.exec_run('hostname')[1].decode('utf-8')
                    real_name_split = path.split('.')
                    real_name = ('.'.join(real_name_split[:-1]))
                try:
                    result = next(machine_stats)
                except StopIteration:
                    continue

                stats = self._get_aggregate_machine_info(result)

                machines_data.append([machine.labels['lab_hash'],
                                      machine.labels['user'],
                                      real_name,
                                      machine.status,
                                      stats["cpu_usage"],
                                      stats["mem_usage"],
                                      stats["mem_percent"],
                                      stats["net_usage"]
                                      ])

            stats_table.table_data = machines_data

            yield "TIMESTAMP: %s" % datetime.now() + "\n\n" + stats_table.table

    @privileged
    def get_machine_info(self, machine_name, recursive, lab_hash=None, all_users=False):
        user_name = utils.get_current_user_name() if not all_users else None

        machines = self.docker_machine.get_machines_by_filters(machine_name=machine_name,
                                                               lab_hash=lab_hash,
                                                               user=user_name
                                                               )

        if not machines:
            raise Exception("The specified machine is not running.")
        elif len(machines) > 1:
            raise Exception("There are more than one machine matching the name `%s`." % machine_name)

        machine = machines[0]

        machine_info = utils.format_headers("Machine information") + "\n"

        machine_info += "Lab Hash: %s\n" % machine.labels['lab_hash']
        machine_info += "Machine Name: %s\n" % machine_name
        machine_info += "Real Machine Name: %s\n" % machine.name
        machine_info += "Status: %s\n" % machine.status
        machine_info += "Image: %s\n\n" % machine.image.tags[0]

        machine_stats = machine.stats(stream=False)

        machine_info += "PIDs: %d\n" % (machine_stats["pids_stats"]["current"]
                                        if "current" in machine_stats["pids_stats"] else 0)
        stats = self._get_aggregate_machine_info(machine_stats)

        machine_info += "CPU Usage: %s\n" % stats["cpu_usage"]
        machine_info += "Memory Usage: %s\n" % stats["mem_usage"]
        machine_info += "Network Usage (DL/UL): %s\n" % stats["net_usage"]

        machine_info += "======================================================================="

        return machine_info

    @privileged
    def check_image(self, image_name):
        self.docker_image.check_and_pull(image_name)

    @privileged
    def check_updates(self, settings):
        local_image_info = self.docker_image.check_local(settings.image)
        remote_image_info = self.docker_image.check_remote(settings.image)

        # Image has been built locally, so there's nothing to compare.
        local_repo_digests = local_image_info.attrs["RepoDigests"]
        if not local_repo_digests:
            return

        local_repo_digest = local_repo_digests[0]
        remote_image_digest = remote_image_info["images"][0]["digest"]

        # Format is image_name@sha256, so we strip the first part.
        (_, local_image_digest) = local_repo_digest.split("@")

        if remote_image_digest != local_image_digest:
            utils.confirmation_prompt("A new version of image `%s` has been found on Docker Hub. "
                                      "Do you want to pull it?" % settings.image,
                                      lambda: self.docker_image.pull(settings.image),
                                      lambda: None
                                      )

    @privileged
    def get_release_version(self):
        return self.client.version()["Version"]

    def get_manager_name(self):
        return "docker"

    def get_formatted_manager_name(self):
        return "Docker (Kathara)"

    @staticmethod
    def _get_aggregate_machine_info(stats):
        network_stats = stats["networks"] if "networks" in stats else {}

        return {
            "cpu_usage": "{0:.2f}%".format(stats["cpu_stats"]["cpu_usage"]["total_usage"] /
                                           stats["cpu_stats"]["system_cpu_usage"]
                                           ) if "system_cpu_usage" in stats["cpu_stats"] else "-",
            "mem_usage": utils.human_readable_bytes(stats["memory_stats"]["usage"]) + " / " +
                         utils.human_readable_bytes(stats["memory_stats"]["limit"])
            if "usage" in stats["memory_stats"] else "- / -",
            "mem_percent": "{0:.2f}%".format((stats["memory_stats"]["usage"] / stats["memory_stats"]["limit"]) * 100)
            if "usage" in stats["memory_stats"] else "-",
            "net_usage": utils.human_readable_bytes(sum([net_stats["rx_bytes"]
                                                         for (_, net_stats) in network_stats.items()])
                                                    ) + " / " +
                         utils.human_readable_bytes(sum([net_stats["tx_bytes"]
                                                         for (_, net_stats) in network_stats.items()])
                                                    )
        }

    # RITORNA IL PATH PER CONNETTERSI AL CLIENT DOCKER DEL CONTAINER PASSATO COME PARAMETRO
    # print(getClient("","milano"))
    # return = proc/16068/root/proc/461/root/
    def foundClient(self, path, name):
        client = docker.DockerClient(base_url="unix://" + path + "run/docker.sock")
        list_container = client.containers.list()
        if len(list_container) == 0:
            return None
        else:
            for container in list_container:
                pid = client.api.inspect_container(container.id)['State']['Pid']
                if self.reverseOfPath(container.exec_run('hostname')[1].strip().decode('utf-8')[:-1]) == name:
                    path += "proc/" + str(pid) + "/root/"
                    return path
                else:
                    final_path = self.foundClient(path + "proc/" + str(pid) + "/root/", name)
                    if final_path:
                        return final_path

    # RITORNA IL CLIENT DEL CONTAINER PASSATO COME PARAMETRO
    def getClient(self, name):
        path = self.foundClient("", self.reverseOfPath(name))
        if path:
            client = docker.DockerClient(base_url="unix://" + path + "run/docker.sock")
            return client
        else:
            raise Exception("getClient: Il container non esiste")

    # Ritorna tutti i client del multilab
    def getAllClient(self, client, list_client):
        list_container = client.containers.list()
        if len(list_container) == 0:
            return []
        else:
            for container in list_container:
                path = container.exec_run('hostname')[1].strip().decode('utf-8')[:-1]
                client = self.getClient(path)
                list_client.append(client)
                self.getAllClient(client, list_client)

    # Restituisce la cartella (intesa come /proc/pid/root) della macchina passata
    def getFolderMachine(self, machine):
        path = self.foundClient("", machine)
        if path:
            return path
        raise Exception("getFolderMachine: Il container non esiste")

    # Ritorna la lista di tutti i path del multilab
    def getAllPath(self):
        list_path = []
        self.getAllPathRecursive(self.client,list_path)
        return list_path

    # Crea la lista di tutti i path del multilab
    def getAllPathRecursive(self,client,list_path):
        list_container = client.containers.list()
        if len(list_container) == 0:
            return []
        else:
            for container in list_container:
                path = container.exec_run('hostname')[1].strip().decode('utf-8')[:-1]
                list_path.append(path)
                client = self.getClient(path)
                self.getAllPathRecursive(client, list_path)

    # Ritorna il client che ha come figlio il container passato come parametro
    # getParentClient(du.mi.com) ritorna il client di milano
    def getParentClient(self, machine):
        machine_split = machine.split('.')
        machine_parent = machine_split[1:]
        machine_parent = '.'.join(machine_parent)
        try:
            client = self.getClient(machine_parent)
            return client
        except Exception as e:
            return self.client

    # Ritorna true se il path è corretto, false altrimenti
    def checkPath(self, machine_name):
        if self.getHostname() != "":
            machine_name += '.' + self.getHostname()
            machine_name = machine_name[:-1]
        client = self.getParentClient(machine_name)
        list_container = client.containers.list()
        for container in list_container:
            if machine_name == container.exec_run('hostname')[1].decode('utf-8').strip()[:-1]:
                return True
        return False

    # Elimina tutti i volumi passati come parametro:
    def delListVolume(self, list_volume):
        for volume in list_volume:
            self.client.volumes.get(volume).remove()

    # Prende tutti i volumi dei container passati come parametro
    def getListVolume(self, list_container):
        list_volume = []
        for container in list_container:
            volume = self.getVolumeById(container.id)
            list_volume.append(volume)
        return list_volume

    # Prende il volume di un container (potrebbe essere una lista?)
    def getVolumeById(self, containerID):
        list_dict = self.client.api.inspect_container(containerID)['Mounts']
        for dictonary in list_dict:
            if dictonary['Type'] == 'volume':
                return dictonary['Name']

    # Prende il volume di un container (potrebbe essere una lista?)
    def getVolumeByName(self, containerName):
        list_dict = self.client.api.inspect_container(containerName)['Mounts']
        for dictonary in list_dict:
            if dictonary['Type'] == 'volume':
                return dictonary['Name']

    # Ritorna un dizionario con i path corretti e path non corretti
    def checkListPath(self, list_path):
        dict_path = {'Correct': [], 'Invalid': []}
        client = self.client
        for path in list_path:
            if self.checkPath(list(reversed(path.split('.'))), client):
                dict_path['Correct'].append(path)
            else:
                dict_path['Invalid'].append(path)
        return dict_path

    # Dato il nome di una machina (firenze.it) ritorna l'id di quella macchina
    def getIdMachine(self, machine):
        name_machine = machine.split('.')[0]
        list_container = self.client.containers.list()
        for container in list_container:
            if name_machine == container.labels['name']:
                return container.id

    # Dato il nome di una macchina (firenze.it) ritorna il container corrispondente
    def getContainerByName(self,machine):
        client = self.getParentClient(machine)
        list_container = client.containers.list()
        for container in list_container:
            if machine == container.exec_run('hostname')[1].strip().decode('utf-8')[:-1]:
                return container
        raise Exception("getContainerByName, container non trovato")

    # Restituisce il grado di una macchina, dove per grado si intende il numero di macchine che compongono
    # il path --> duomo.milano.com ha grado 3, com ha grado 1
    @staticmethod
    def getDegree(machine):
        return len(machine.split('.'))

    # Restituisce True se due macchine fanno parte dello stesso path --> duomo.milano.com e milano.com si.
    # False altrimenti --> firenze.it e roma.com no
    def samePath(self, machine1, machine2):
        degree1 = self.getDegree(machine1)
        degree2 = self.getDegree(machine2)
        def_degree = degree1 - degree2
        if machine1.split('.')[def_degree:] == machine2.split('.'):
            return True
        return False

    # Effettua l'eliminazione di una macchina se nella lista c'è una macchina con grado minore e stesso path
    def filterMachinePath(self, first_machine, list_machine, copy_list):
        for machine in copy_list:
            if self.samePath(first_machine, machine):
                if self.getDegree(first_machine) > self.getDegree(machine):
                    list_machine.remove(first_machine)
                    break
        return list_machine

    # Data una lista di macchine da eliminare, toglie dalla lista quelle macchine che vengono già eliminate
    # dalla cancellazione di un loro antenato. (firenze.it,milano.com,duomo.milano.com,com) --> (firenze.it,com)
    def getFilterMachinePath(self, list_machine):
        copy_list = []
        copy_list.extend(list_machine)
        for machine in copy_list:
            self.filterMachinePath(machine, list_machine, copy_list)
        return list_machine

    # Inverte un path (com.milano.duomo -> duomo.milano.com)
    @staticmethod
    def reverseOfPath(path):
        list_split_path = path.split('.')
        list_split_path = list(reversed(list_split_path))
        path = ('.'.join(list_split_path))
        return path

    # Ritorna l'hostname della macchina
    def getHostname(self):
        f = open("/etc/hostname", 'r')
        hostname = f.read()
        hostname_split = hostname.split('.')
        if len(hostname_split) == 1:
            return ""
        hostname = ('.'.join(hostname_split))
        strange = hostname[-1]
        hostname = hostname.replace(strange, "")
        return hostname

    # Data una network A.milano.com ritorna la macchina corrispondente milano.com
    @staticmethod
    def getMachineByNetwork(network):
        network_split = network.split('.')
        network_split.pop(0)
        machine = ('.'.join(network_split))
        return machine

    # Data una macchina, ritorna la lista di macchine che compongono il path della macchina in input
    # duomo.milano.com -> [duomo.milano.com,milano.com,com]
    def getListPath(self, machine):
        list_path = []
        if machine == "":
            return list_path
        path = ""
        for c in machine:
            path += c
            if c == '.':
                list_path.append(self.reverseOfPath(path[:-1]))
        list_path.append(self.reverseOfPath(path))
        return list_path

    # Crea un collegamento tra due domini di collisione
    def connect_domain(self, network1, network2):
        machine1 = self.getMachineByNetwork(network1)
        machine2 = self.getMachineByNetwork(network2)
        machine1 = [item for item in machine1.split('.') if item not in utils.getHostname().split('.')]
        machine2 = [item for item in machine2.split('.') if item not in utils.getHostname().split('.')]
        machine1 = ('.'.join(machine1))
        machine2 = ('.'.join(machine2))
        if (self.checkPath(machine1) or machine1 == "") and (self.checkPath(machine2) or machine2 == ""):
            networking = Networking()
            name_veth1 = networking.random_veth_name()
            name_veth2 = networking.random_veth_name()
            networking.create_veth(name_veth1, name_veth2)
            if machine1 == "" and machine2 == "":
                networking.up_network(name_veth1, self.getBridgeClient(network1))
                networking.up_network(name_veth2, self.getBridgeClient(network2))
            else:
                if machine1 == "":
                    container2 = self.getContainerByName(machine2)
                    self.move_veth(machine2, name_veth2, container2)
                    networking.up_network(name_veth1, self.getBridgeClient(network1))
                    self.up_veth(name_veth2, container2, network2)
                if machine2 == "":
                    container1 = self.getContainerByName(machine1)
                    self.move_veth(machine1, name_veth1, container1)
                    networking.up_network(name_veth2, self.getBridgeClient(network2))
                    self.up_veth(name_veth1, container1, network1)
                if machine1 != "" and machine2 != "":
                    container1 = self.getContainerByName(machine1)
                    container2 = self.getContainerByName(machine2)
                    self.move_veth(machine1, name_veth1, container1)
                    self.move_veth(machine2, name_veth2, container2)
                    self.up_veth(name_veth1, container1, network1)
                    self.up_veth(name_veth2, container2, network2)
        else:
            raise Exception("Invalid path")

    # Ritorna il bridge del dominio passato
    def getBridgeClient(self, network):
        machine = ('.'.join(network.split('.')[1:-1]))
        if self.getHostname()[:-1] == machine:
            client = self.client
        else:
            client = self.getClient(machine)
        complete_network = self.docker_link.get_network_name(network)
        if len(machine.split('.')) > 0 and machine != "":
            complete_network = complete_network.replace(utils.get_current_user_name(), "root")
        list_network = client.networks.list()
        id_network = ""
        for net in list_network:
            if net.name == complete_network:
                id_network = net.id
        bridge = id_network[:12]
        if bridge:
            return bridge
        else:
            raise Exception("Il dominio %s non esiste", network)

    @staticmethod
    def getParentMachine(machine):
        machine_split = machine.split('.')
        if len(machine_split) == 1:
            return ""
        machine = ('.'.join(machine_split[1:]))
        return machine

    # Sposta la veth fino alla macchina passata come parametro
    def move_veth(self, machine1, name_veth1, container):
        networking = Networking()
        list_path1 = self.getListPath(self.reverseOfPath(machine1))
        pid = docker.APIClient().inspect_container(container.name)["State"]["Pid"]
        networking.move_veth(name_veth1, pid)
        list_path1.pop(0)
        if len(list_path1) > 0:
            for path1 in list_path1:
                folder_container_parent = self.getFolderMachine(self.getParentMachine(path1))
                container = self.getContainerByName(path1)
                pid1 = docker.APIClient(base_url="unix://" + folder_container_parent + \
                                                 "run/docker.sock").inspect_container(container.name)["State"]["Pid"]
                parent_container = self.getContainerByName(self.getParentMachine(path1))
                parent_container.exec_run(['python3', '/shared/move_veth.py', name_veth1, str(pid1)])

    # Uppa la veth delle 2 macchine passate come parametro
    def up_veth(self, name_veth1, container1, network1):
        bridge1 = self.getBridgeClient(network1)
        container1.exec_run(['python3', '/shared/up_network.py', name_veth1, bridge1])

    # Runna il multilab
    def runNestedLab(self, lab):
        time.sleep(2)
        list_container = self.client.containers.list()
        networking = Networking()
        path_image = self.getPathImage(lab)
        if len(self.getHostname().split('.')) > 1:
            for container in list_container:
                pid = docker.APIClient().inspect_container(container.name)["State"]["Pid"]
                bash('ln -s /proc/' + str(pid) + '/ns/net /var/run/netns/' + str(pid))
                if os.path.isdir('/sublab/' + container.labels['name'] + '/sublab'):
                    bash("cp -a /shared /sublab")
                    container_connect = container.exec_run('hostname')[1].strip().decode('utf-8')
                    client = self.getClient(container_connect[:-1])
                    with open(path_image, 'rb') as f:
                        client.images.load(f)
                    container.exec_run(['python3', '/shared/src/kathara.py', 'lstart', '-d', '/sublab', '--privileged'])

        else:
            networking.create_namespace(self.client.containers.list())
            for container in list_container:
                path_container = os.path.join(lab.path, container.labels['name'], "sublab")
                if os.path.exists(path_container):
                    pid = docker.APIClient().inspect_container(container.name)["State"]["Pid"]
                    client = self.getClient(container.labels['name'])
                    with open(path_image, 'rb') as f:
                        client.images.load(f)
                    container.exec_run(['python3', '/shared/src/kathara.py', 'lstart', '-d', '/sublab', '--privileged'])

    # ritorna il path dell'immagine docker
    def getPathImage(self, lab):
        len_split = len(self.getHostname().split('.'))
        if len_split == 1:
            return lab.path + '/image/dind-kathara.tar'
        else:
            return "/root/dind-kathara.tar"

    # Data una lista di container, ritorna una lista dei nomi delle macchine
    @staticmethod
    def getNameContainerByList(list_container):
        list_name = []
        for container in list_container:
            list_name.append(container.labels['name'])
        return list_name

    # Metodo che crea i collegamenti tra domini espressi in lab.int
    def createDomain(self, lab):
        import mmap
        import re
        path = lab.path
        lab_int_path = os.path.join(path, 'lab.int')
        # Reads lab.conf in memory so it is faster.
        if os.path.exists(lab_int_path):
            with open(lab_int_path, 'r') as lab_file:
                lab_mem_file = mmap.mmap(lab_file.fileno(), 0, access=mmap.ACCESS_READ)
            line_number = 1
            line = lab_mem_file.readline().decode('utf-8')

            while line:
                matches = re.search(r"^(?P<key>\"(\w+.)+\")=(?P<value>\"(\w+.)+\")$",
                                    line.strip()
                                    )
                if matches:
                    # Deve essere locale alla macchina che legge il lab.int
                    key = matches.group("key").replace('"', '').replace("'", '')
                    # Dominio diverso da quello della macchina che legge il lab.int
                    value = matches.group("value").replace('"', '').replace("'", '')
                    self.connect_domain(key, value)

                line_number += 1
                line = lab_mem_file.readline().decode('utf-8')

