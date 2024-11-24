import logging
import re
import shlex
import sys
import time
from itertools import islice
from multiprocessing.dummy import Pool
from typing import List, Dict, Generator, Optional, Set, Tuple, Union, Any

import chardet
import docker.models.containers
from docker import DockerClient
from docker.errors import APIError
from docker.types import Ulimit
from docker.utils import version_lt, version_gte

from .DockerImage import DockerImage
from .stats.DockerMachineStats import DockerMachineStats
from ... import utils
from ...event.EventDispatcher import EventDispatcher
from ...exceptions import MountDeniedError, MachineAlreadyExistsError, DockerPluginError, \
    MachineBinaryError, MachineNotRunningError, PrivilegeError, InvocationError
from ...model.Interface import Interface
from ...model.Lab import Lab
from ...model.Link import Link, BRIDGE_LINK_NAME
from ...model.Machine import Machine, MACHINE_CAPABILITIES
from ...setting.Setting import Setting
from ...utils import parse_docker_engine_version

RP_FILTER_NAMESPACE = "net.ipv4.conf.%s.rp_filter"
OCI_RUNTIME_RE = re.compile(
    r"OCI runtime exec failed(.*?)(stat (.*): no such file or directory|exec: \"(.*)\": executable file not found)"
)

# Known commands that each container should execute
# Run order: shared.startup, machine.startup and machine.meta['exec_commands']
STARTUP_COMMANDS = [
    # Unmount the /etc/resolv.conf and /etc/hosts files, automatically mounted by Docker inside the container.
    # In this way, they can be overwritten by custom user files.
    "umount /etc/resolv.conf",
    "umount /etc/hosts",

    # Copy the machine folder (if present) from the hostlab directory into the root folder of the container
    # In this way, files are all replaced in the container root folder
    "if [ -d \"/hostlab/{machine_name}\" ]; then "
    "(cd /hostlab/{machine_name} && tar c .) | (cd / && tar xhf - --no-same-owner --no-same-permissions); fi",

    # If /etc/hosts is not configured by the user, add the localhost mapping
    "if [ ! -s \"/etc/hosts\" ]; then "
    "echo '127.0.0.1 localhost' > /etc/hosts",
    "echo '::1 localhost' >> /etc/hosts",
    "fi",

    # Give proper permissions to /var/www
    "if [ -d \"/var/www\" ]; then "
    "chmod -R 777 /var/www/*; fi",

    # Give proper permissions to Quagga files (if present)
    "if [ -d \"/etc/quagga\" ]; then "
    "chown -R quagga:quagga /etc/quagga/",
    "chmod 640 /etc/quagga/*; fi",

    # Give proper permissions to FRR files (if present)
    "if [ -d \"/etc/frr\" ]; then "
    "chown -R frr:frr /etc/frr/",
    "chmod 640 /etc/frr/*; fi",

    # If shared.startup file is present
    "if [ -f \"/hostlab/shared.startup\" ]; then "
    # Give execute permissions to the file and execute it
    # We redirect the output "&>" to a debugging file
    "chmod u+x /hostlab/shared.startup",
    # Adds a line to enable command output
    "sed -i \"1s;^;set -x\\n\\n;\" /hostlab/shared.startup",
    "/hostlab/shared.startup &> /var/log/shared.log; fi",

    # If .startup file is present
    "if [ -f \"/hostlab/{machine_name}.startup\" ]; then "
    # Give execute permissions to the file and execute it
    # We redirect the output "&>" to a debugging file
    "chmod u+x /hostlab/{machine_name}.startup",
    # Adds a line to enable command output
    "sed -i \"1s;^;set -x\\n\\n;\" /hostlab/{machine_name}.startup",
    "/hostlab/{machine_name}.startup &> /var/log/startup.log; fi",

    # Placeholder for user commands
    "{machine_commands}",

    "touch /tmp/EOS"
]

SHUTDOWN_COMMANDS = [
    # If machine.shutdown file is present
    "if [ -f \"/hostlab/{machine_name}.shutdown\" ]; then "
    # Give execute permissions to the file and execute it
    "chmod u+x /hostlab/{machine_name}.shutdown; /hostlab/{machine_name}.shutdown; fi",

    # If shared.shutdown file is present
    "if [ -f \"/hostlab/shared.shutdown\" ]; then "
    # Give execute permissions to the file and execute it
    "chmod u+x /hostlab/shared.shutdown; /hostlab/shared.shutdown; fi"
]


class DockerMachine(object):
    """The class responsible for deploying Kathara devices as Docker container and interact with them."""
    __slots__ = ['client', '_engine_version', 'docker_image']

    def __init__(self, client: DockerClient, docker_image: DockerImage) -> None:
        self.client: DockerClient = client
        self._engine_version: str = parse_docker_engine_version(client.version()['Version'])
        self.docker_image: DockerImage = docker_image

    def deploy_machines(self, lab: Lab, selected_machines: Set[str] = None, excluded_machines: Set[str] = None) -> None:
        """Deploy all the network scenario devices as Docker containers.

        Args:
            lab (Kathara.model.Lab.Lab): A Kathara network scenario.
            selected_machines (Set[str]): A set containing the name of the devices to deploy.
            excluded_machines (Set[str]): A set containing the name of the devices to exclude.

        Returns:
            None

        Raises:
            PrivilegeError: If the privileged mode is active and the user does not have root privileges.
            InvocationError: If both `selected_machines` and `excluded_machines` are specified.
        """
        if lab.general_options['privileged_machines'] and not utils.is_admin():
            raise PrivilegeError("You must be root in order to start Kathara devices in privileged mode.")

        if selected_machines and excluded_machines:
            raise InvocationError(f"You can either specify `selected_machines` or `excluded_machines`.")

        machines = lab.machines.items()
        if selected_machines:
            machines = {
                k: v for k, v in machines if k in selected_machines
            }.items()
        elif excluded_machines:
            machines = {
                k: v for k, v in machines if k not in excluded_machines
            }.items()

        # Check and pulling machine images
        lab_images = set(map(lambda x: x[1].get_image(), machines))
        self.docker_image.check_from_list(lab_images)

        shared_mount = lab.general_options['shared_mount'] if 'shared_mount' in lab.general_options \
            else Setting.get_instance().shared_mount
        if shared_mount:
            if Setting.get_instance().remote_url is not None:
                logging.warning("Shared folder cannot be mounted with a remote Docker connection.")
            else:
                lab.create_shared_folder()

        EventDispatcher.get_instance().dispatch("machines_deploy_started", items=machines)

        # Deploy all lab machines.
        # If there is no lab.dep file, machines can be deployed using multithreading.
        # If not, they're started sequentially
        if not lab.has_dependencies:
            pool_size = utils.get_pool_size()
            items = utils.chunk_list(machines, pool_size)

            with Pool(pool_size) as machines_pool:
                for chunk in items:
                    machines_pool.map(func=self._deploy_and_start_machine, iterable=chunk)
        else:
            for item in machines:
                self._deploy_and_start_machine(item)

        EventDispatcher.get_instance().dispatch("machines_deploy_ended")

    def _deploy_and_start_machine(self, machine_item: Tuple[str, Machine]) -> None:
        """Deploy and start a Docker container from the device contained in machine_item.

        Args:
            machine_item (Tuple[str, Machine]): A tuple composed by the name of the device and a device object

        Returns:
            None
        """
        (_, machine) = machine_item

        self.create(machine)
        self.start(machine)

        EventDispatcher.get_instance().dispatch("machine_deployed", item=machine)

    def create(self, machine: Machine) -> None:
        """Create a Docker container representing the device and assign it to machine.api_object.

        Args:
            machine (Kathara.model.Machine.Machine): A Kathara device.

        Returns:
            None

        Raises:
            MachineAlreadyExistsError: If a device with the name specified already exists.
            APIError: If the Docker APIs return an error.
        """
        logging.debug("Creating device `%s`..." % machine.name)

        containers = self.get_machines_api_objects_by_filters(machine_name=machine.name, lab_hash=machine.lab.hash,
                                                              user=utils.get_current_user_name())
        if containers:
            raise MachineAlreadyExistsError(machine.name)

        image = machine.get_image()
        memory = machine.get_mem()
        cpus = machine.get_cpu(multiplier=1000000000)
        ulimits = [Ulimit(name=k, soft=v["soft"], hard=v["hard"]) for k, v in machine.get_ulimits().items()]

        ports_info = machine.get_ports()
        ports = None
        if ports_info:
            ports = {}
            for (host_port, protocol), guest_port in ports_info.items():
                ports['%d/%s' % (guest_port, protocol)] = host_port

        # Get the global machine metadata into a local variable (just to avoid accessing the lab object every time)
        global_machine_metadata = machine.lab.global_machine_metadata

        # If bridged is required in command line but not defined in machine meta, add it.
        if "bridged" in global_machine_metadata and not machine.is_bridged():
            machine.add_meta("bridged", True)

        if ports and not machine.is_bridged():
            logging.warning(
                "To expose ports of device `%s` on the host, "
                "you have to specify the `bridged` option on that device." % machine.name
            )

        # If any exec command is passed in command line, add it.
        if "exec" in global_machine_metadata:
            machine.add_meta("exec", global_machine_metadata["exec"])

        # Get the first network object, if defined.
        # This should be used in container create function
        first_network = None
        first_machine_iface = None
        if machine.interfaces:
            first_machine_iface = machine.interfaces[0]
            first_network = first_machine_iface.link.api_object

        # If no interfaces are declared in machine, but bridged mode is required, get bridge as first link.
        # Flag that bridged is already connected (because there's another check in `start`).
        if first_machine_iface is None and machine.is_bridged():
            first_network = machine.lab.get_or_new_link(BRIDGE_LINK_NAME).api_object
            machine.add_meta("bridge_connected", True)

        # Sysctl params to pass to the container creation
        sysctl_parameters = {RP_FILTER_NAMESPACE % x: 0 for x in ["all", "default", "lo"]}
        sysctl_parameters["net.ipv4.ip_forward"] = 1
        sysctl_parameters["net.ipv4.icmp_ratelimit"] = 0

        sysctl_first_interface = {}
        if first_machine_iface:
            if version_lt(self._engine_version, "26.0.0"):
                sysctl_first_interface = {RP_FILTER_NAMESPACE % "eth0": 0}

        if machine.is_ipv6_enabled():
            sysctl_parameters["net.ipv6.conf.all.forwarding"] = 1
            sysctl_parameters["net.ipv6.conf.all.accept_ra"] = 0
            sysctl_parameters["net.ipv6.icmp.ratelimit"] = 0
            sysctl_parameters["net.ipv6.conf.default.disable_ipv6"] = 0
            sysctl_parameters["net.ipv6.conf.all.disable_ipv6"] = 0
        else:
            sysctl_parameters["net.ipv6.conf.default.disable_ipv6"] = 1
            sysctl_parameters["net.ipv6.conf.all.disable_ipv6"] = 1
            sysctl_parameters["net.ipv6.conf.default.forwarding"] = 0
            sysctl_parameters["net.ipv6.conf.all.forwarding"] = 0

        # Merge machine sysctls
        sysctl_parameters = {**sysctl_parameters, **machine.meta['sysctls'], **sysctl_first_interface}

        volumes = {}

        lab_options = machine.lab.general_options
        shared_mount = ['shared_mount'] if 'shared_mount' in lab_options else Setting.get_instance().shared_mount
        if shared_mount and machine.lab.shared_path:
            volumes[machine.lab.shared_path] = {'bind': '/shared', 'mode': 'rw'}

        # Mount the host home only if specified in settings.
        hosthome_mount = lab_options['hosthome_mount'] if 'hosthome_mount' in lab_options else \
            Setting.get_instance().hosthome_mount
        if hosthome_mount and Setting.get_instance().remote_url is None:
            volumes[utils.get_current_user_home()] = {'bind': '/hosthome', 'mode': 'rw'}

        privileged = lab_options['privileged_machines']
        if Setting.get_instance().remote_url is not None and privileged:
            privileged = False
            logging.warning("Privileged flag is ignored with a remote Docker connection.")

        networking_config = None
        if first_machine_iface:
            driver_opt = self._create_driver_opt(machine, first_machine_iface)

            networking_config = {
                first_network.name: self.client.api.create_endpoint_config(
                    driver_opt=driver_opt
                )
            }

        container_name = self.get_container_name(machine.name, machine.lab.hash)

        try:
            machine_container = self.client.containers.create(image=image,
                                                              name=container_name,
                                                              hostname=machine.name,
                                                              cap_add=MACHINE_CAPABILITIES if not privileged else None,
                                                              privileged=privileged,
                                                              network=first_network.name if first_network else None,
                                                              network_mode="bridge" if first_network else "none",
                                                              networking_config=networking_config,
                                                              environment=machine.meta['envs'],
                                                              sysctls=sysctl_parameters,
                                                              mem_limit=memory,
                                                              nano_cpus=cpus,
                                                              ports=ports,
                                                              tty=True,
                                                              stdin_open=True,
                                                              detach=True,
                                                              volumes=volumes,
                                                              labels={"name": machine.name,
                                                                      "lab_hash": machine.lab.hash,
                                                                      "user": utils.get_current_user_name(),
                                                                      "app": "kathara",
                                                                      "shell": machine.meta["shell"]
                                                                      if "shell" in machine.meta
                                                                      else Setting.get_instance().device_shell
                                                                      },
                                                              ulimits=ulimits
                                                              )
        except APIError as e:
            raise e

        # Pack machine files into a tar.gz and extract its content inside `/`
        tar_data = machine.pack_data()
        if tar_data:
            self.copy_files(machine_container, "/", tar_data)

        machine.api_object = machine_container

    def connect_interface(self, machine: Machine, interface: Interface) -> None:
        """Connect the Docker container representing the machine to a specified collision domain.

        Args:
            machine (Kathara.model.Machine.Machine): A Kathara device.
            interface (Kathara.model.Interface.Interface): A Kathara interface object.

        Returns:
            None

        Raises:
            DockerPluginError: If Kathara has been left in an inconsistent state.
            APIError: If the Docker APIs return an error.
        """
        attached_networks = machine.api_object.attrs["NetworkSettings"]["Networks"]

        if interface.link.api_object.name not in attached_networks:
            driver_opt = self._create_driver_opt(machine, interface)
            try:
                interface.link.api_object.connect(
                    machine.api_object,
                    driver_opt=driver_opt
                )
            except APIError as e:
                if e.response.status_code == 500 and \
                        ("network does not exist" in e.explanation or "endpoint does not exist" in e.explanation):
                    raise DockerPluginError(
                        "Kathara has been left in an inconsistent state! Please run `kathara wipe`.")
                else:
                    raise e

    def _create_driver_opt(self, machine: Machine, interface: Interface) -> dict[str, str]:
        """Create a dict containing the default network driver options for a device.

        Args:
            machine (Kathara.model.Machine.Machine): The Kathara device to be attached to the interface.
            interface (Kathara.model.Interface.Interface): The interface to be attached to the device.

        Returns:
            dict[str, str]: A dict containing the default network driver options for a device.
        """
        driver_opt = {'kathara.iface': str(interface.num), 'kathara.link': interface.link.name}
        if version_gte(self._engine_version, "27.0.0"):
            sysctl_opts = ["net.ipv4.conf.IFNAME.rp_filter=0"]

            if machine.is_ipv6_enabled():
                sysctl_opts.extend(["net.ipv6.conf.IFNAME.disable_ipv6=0", "net.ipv6.conf.IFNAME.forwarding=1"])
            else:
                sysctl_opts.append("net.ipv6.conf.IFNAME.disable_ipv6=1")

            driver_opt["com.docker.network.endpoint.sysctls"] = ",".join(sysctl_opts)

        if interface.mac_address:
            driver_opt['kathara.mac_addr'] = interface.mac_address

        return driver_opt

    @staticmethod
    def disconnect_from_link(machine: Machine, link: Link) -> None:
        """Disconnect the Docker container representing the machine from a specified collision domain.

        Args:
            machine (Kathara.model.Machine): A Kathara device.
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None
        """
        attached_networks = machine.api_object.attrs["NetworkSettings"]["Networks"]

        if link.api_object.name in attached_networks:
            link.api_object.disconnect(machine.api_object)

    def start(self, machine: Machine) -> None:
        """Start the Docker container representing the device.

        Connect the container to the networks, run the startup commands and open a terminal (if requested).

        Args:
           machine (Kathara.model.Machine.Machine): A Kathara device.

        Returns:
            None

        Raises:
            MountDeniedError: If the host drive is not shared with Docker.
            DockerPluginError: If Kathara has been left in an inconsistent state.
            APIError: If the Docker APIs return an error.
        """
        logging.debug("Starting device `%s`..." % machine.name)

        try:
            machine.api_object.start()
        except APIError as e:
            if e.response.status_code == 500 and e.explanation.startswith('Mounts denied'):
                raise MountDeniedError("Host drive is not shared with Docker.")
            elif e.response.status_code == 500 and \
                    ("network does not exist" in e.explanation or "endpoint does not exist" in e.explanation):
                raise DockerPluginError("Kathara has been left in an inconsistent state! Please run `kathara wipe`.")
            else:
                raise e

        # Connect the container to its networks (starting from the second, the first is already connected in `create`)
        # This should be done after the container start because Docker causes a non-deterministic order when attaching
        # networks before container startup.
        for (iface_num, machine_iface) in islice(machine.interfaces.items(), 1, None):
            logging.debug(
                f"Connecting device `{machine.name}` to collision domain `{machine_iface.link.name}` "
                f"on interface {iface_num}..."
            )
            self.connect_interface(machine, machine_iface)

        # Bridged connection required but not added in `deploy` method.
        if "bridge_connected" not in machine.meta and machine.is_bridged():
            bridge_link = machine.lab.get_or_new_link(BRIDGE_LINK_NAME).api_object
            bridge_link.connect(machine.api_object)

        # Append executed machine startup commands inside the /var/log/startup.log file
        if machine.meta['exec_commands']:
            new_commands = []
            for command in machine.meta['exec_commands']:
                new_commands.append("echo \"++ %s\" &>> /var/log/startup.log" % command)
                new_commands.append(command)
            machine.meta['exec_commands'] = new_commands

        # Build the final startup commands string
        startup_commands_string = "; ".join(STARTUP_COMMANDS).format(
            machine_name=machine.name,
            machine_commands="; ".join(machine.meta['exec_commands']) if machine.meta['exec_commands'] else ":"
        )

        logging.debug(f"Executing startup command on `{machine.name}`: {startup_commands_string}")

        try:
            # Execute the startup commands inside the container (without privileged flag so basic permissions are used)
            self._exec_run(machine.api_object,
                           cmd=[machine.api_object.labels['shell'], '-c', startup_commands_string],
                           stdout=True,
                           stderr=True,
                           privileged=False,
                           detach=True
                           )
        except MachineBinaryError as e:
            machine.add_meta('num_terms', 0)

            logging.warning(f"Shell `{e.binary}` not found in "
                            f"image `{machine.get_image()}` of device `{machine.name}`. "
                            f"Startup commands will not be executed and terminal will not open. "
                            f"Please specify a valid shell for this device."
                            )

        machine.api_object.reload()

    def undeploy(self, lab_hash: str, selected_machines: Set[str] = None, excluded_machines: Set[str] = None) -> None:
        """Undeploy the devices contained in the network scenario defined by the lab_hash.

        If a set of selected_machines is specified, undeploy only the specified devices.

        Args:
            lab_hash (str): The hash of the network scenario to undeploy.
            selected_machines (Set[str]): A set containing the name of the devices to undeploy.
            excluded_machines (Set[str]): A set containing the name of the devices to exclude.

        Returns:
            None

        Raises:
            InvocationError: If both `selected_machines` and `excluded_machines` are specified.
        """
        if selected_machines and excluded_machines:
            raise InvocationError(f"You can either specify `selected_machines` or `excluded_machines`.")

        containers = self.get_machines_api_objects_by_filters(lab_hash=lab_hash, user=utils.get_current_user_name())
        if selected_machines:
            containers = [item for item in containers if item.labels["name"] in selected_machines]
        elif excluded_machines:
            containers = [item for item in containers if item.labels["name"] not in excluded_machines]

        if len(containers) > 0:
            pool_size = utils.get_pool_size()
            items = utils.chunk_list(containers, pool_size)

            EventDispatcher.get_instance().dispatch("machines_undeploy_started", items=containers)

            with Pool(pool_size) as machines_pool:
                for chunk in items:
                    machines_pool.map(func=self._undeploy_machine, iterable=chunk)

            EventDispatcher.get_instance().dispatch("machines_undeploy_ended")

    def wipe(self, user: str = None) -> None:
        """Undeploy all the running devices of the specified user. If user is None, it undeploy all the running devices.

        Args:
            user (str): The name of a current user on the host.

        Returns:
            None
        """
        containers = self.get_machines_api_objects_by_filters(user=user)

        pool_size = utils.get_pool_size()
        items = utils.chunk_list(containers, pool_size)

        with Pool(pool_size) as machines_pool:
            for chunk in items:
                machines_pool.map(func=self._undeploy_machine, iterable=chunk)

    def _undeploy_machine(self, machine_api_object: docker.models.containers.Container) -> None:
        """Undeploy a Docker container.

        Args:
            machine_api_object (docker.models.containers.Container): The Docker container to undeploy.

        Returns:
            None
        """
        self._delete_machine(machine_api_object)

        EventDispatcher.get_instance().dispatch("machine_undeployed", item=machine_api_object)

    def connect(self, lab_hash: str, machine_name: str, user: str = None, shell: str = None,
                logs: bool = False, wait: Union[bool, Tuple[int, float]] = True) -> None:
        """Open a stream to the Docker container specified by machine_name using the specified shell.

        Args:
            lab_hash (str): The hash of the network scenario containing the device.
            machine_name (str): The name of the device to connect.
            user (str): The name of a current user on the host.
            shell (str): The path to the desired shell.
            logs (bool): If True, print the logs of the startup command.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before giving control to the user. If a tuple is provided, the first value indicates the
                number of retries before stopping waiting and the second value indicates the time interval to wait
                for each retry. Default is True.

        Returns:
            None

        Raises:
            MachineNotRunningError: If the specified device is not running.
            ValueError: If the wait values is neither a boolean nor a tuple, or an invalid tuple.
        """
        containers = self.get_machines_api_objects_by_filters(lab_hash=lab_hash, machine_name=machine_name, user=user)
        if not containers:
            raise MachineNotRunningError(machine_name)
        container = containers.pop()

        if not shell:
            shell = shlex.split(container.labels['shell'])
        else:
            shell = shlex.split(shell)

        logging.debug("Connect to device `%s` with shell: %s" % (machine_name, shell))

        if isinstance(wait, tuple):
            if len(wait) != 2:
                raise ValueError("Invalid `wait` value.")

            n_retries, retry_interval = wait
            should_wait = True
        elif isinstance(wait, bool):
            n_retries = None
            retry_interval = 1
            should_wait = wait
        else:
            raise ValueError("Invalid `wait` value.")

        startup_waited = False
        if should_wait:
            startup_waited = self._wait_startup_execution(container, n_retries=n_retries, retry_interval=retry_interval)

            EventDispatcher.get_instance().dispatch("machine_startup_wait_ended")

        if logs and Setting.get_instance().print_startup_log:
            # Get the logs, if the command fails it means that the shell is not found.
            cat_logs_cmd = "cat /var/log/shared.log /var/log/startup.log"
            startup_command = [item for item in shell]
            startup_command.extend(['-c', cat_logs_cmd])
            exec_result = self._exec_run(container,
                                         cmd=startup_command,
                                         stdout=True,
                                         stderr=False,
                                         privileged=False,
                                         detach=False
                                         )
            char_encoding = chardet.detect(exec_result['output']) if exec_result['output'] else None
            startup_output = exec_result['output'].decode(char_encoding['encoding']) if exec_result['output'] else None

            if startup_output:
                sys.stdout.write("--- Startup Commands Log\n")
                sys.stdout.write(startup_output)
                sys.stdout.write("--- End Startup Commands Log\n")

                if not startup_waited:
                    sys.stdout.write("!!! Executing other commands in background !!!\n")

                sys.stdout.flush()

        resp = self.client.api.exec_create(container.id,
                                           shell,
                                           stdout=True,
                                           stderr=True,
                                           stdin=True,
                                           tty=True,
                                           privileged=False
                                           )

        exec_output = self.client.api.exec_start(resp['Id'],
                                                 tty=True,
                                                 socket=True
                                                 )

        def tty_connect():
            from .terminal.DockerTTYTerminal import DockerTTYTerminal
            DockerTTYTerminal(exec_output, self.client, resp['Id']).start()

        def cmd_connect():
            from .terminal.DockerNPipeTerminal import DockerNPipeTerminal
            DockerNPipeTerminal(exec_output, self.client, resp['Id']).start()

        utils.exec_by_platform(tty_connect, cmd_connect, tty_connect)

    def exec(self, lab_hash: str, machine_name: str, command: Union[str, List], user: str = None,
             tty: bool = True, wait: Union[bool, Tuple[int, float]] = False, stream: bool = True) \
            -> Union[Generator[Tuple[bytes, bytes], None, None], Tuple[bytes, bytes, int]]:
        """Execute the command on the Docker container specified by the lab_hash and the machine_name.

        Args:
            lab_hash (str): The hash of the network scenario containing the device.
            machine_name (str): The name of the device.
            user (str): The name of a current user on the host.
            command (Union[str, List]): The command to execute.
            tty (bool): If True, open a new tty.
            wait (Union[bool, Tuple[int, float]]): If True, wait indefinitely until the end of the startup commands
                execution before executing the command. If a tuple is provided, the first value indicates the
                number of retries before stopping waiting and the second value indicates the time interval to
                wait for each retry. Default is False.
            stream (bool): If True, return a generator object containing the stdout and the stderr of the command.
                If False, returns a tuple containing the complete stdout, the stderr, and the return code of the command.

        Returns:
             Union[Generator[Tuple[bytes, bytes]], Tuple[bytes, bytes, int]]: A generator of tuples containing the stdout
             and stderr in bytes or a tuple containing the stdout, the stderr and the return code of the command.

        Raises:
            MachineNotRunningError: If the specified device is not running.
            MachineBinaryError: If the binary of the command is not found.
            ValueError: If the wait values is neither a boolean nor a tuple, or an invalid tuple.
        """
        logging.debug("Executing command `%s` to device with name: %s" % (command, machine_name))

        containers = self.get_machines_api_objects_by_filters(lab_hash=lab_hash, machine_name=machine_name, user=user)
        if not containers:
            raise MachineNotRunningError(machine_name)
        container = containers.pop()

        if isinstance(wait, tuple):
            if len(wait) != 2:
                raise ValueError("Invalid `wait` value.")

            n_retries, retry_interval = wait
            should_wait = True
        elif isinstance(wait, bool):
            n_retries = None
            retry_interval = 1
            should_wait = wait
        else:
            raise ValueError("Invalid `wait` value.")

        if should_wait:
            self._wait_startup_execution(container, n_retries=n_retries, retry_interval=retry_interval)

        command = shlex.split(command) if type(command) is str else command
        exec_result = self._exec_run(container,
                                     cmd=command,
                                     stdout=True,
                                     stderr=True,
                                     tty=tty,
                                     privileged=False,
                                     stream=stream,
                                     demux=True,
                                     detach=False
                                     )

        if stream:
            return exec_result['output']

        return exec_result['output'][0], exec_result['output'][1], exec_result['exit_code']

    def _exec_run(self, container: docker.models.containers.Container,
                  cmd: Union[str, List], stdout=True, stderr=True, stdin=False, tty=False,
                  privileged=False, user='', detach=False, stream=False,
                  socket=False, environment=None, workdir=None,
                  demux=False) -> Dict[str, Optional[Any]]:
        """Custom implementation of the `exec_run` method that also checks if the executed binary exists.

        Args:
            container (docker.models.containers.Container): Container object on which the command is executed.
            cmd (str or list): Command to be executed
            stdout (bool): Attach to stdout. Default: ``True``
            stderr (bool): Attach to stderr. Default: ``True``
            stdin (bool): Attach to stdin. Default: ``False``
            tty (bool): Allocate a pseudo-TTY. Default: False
            privileged (bool): Run as privileged.
            user (str): User to execute command as. Default: root
            detach (bool): If true, detach from the exec command. Default: False
            stream (bool): Stream response data. Default: False
            socket (bool): Return the connection socket to allow custom read/write operations. Default: False
            environment (dict or list): A dictionary or a list of strings in the following format
                ``["PASSWORD=xxx"]`` or ``{"PASSWORD": "xxx"}``.
            workdir (str): Path to working directory for this exec session
            demux (bool): Return stdout and stderr separately

        Returns:
            (Dict): A dict of (exit_code, output)
                exit_code: (int):
                    Exit code for the executed command or ``None`` if
                    either ``stream`` or ``socket`` is ``True``.
                output: (generator, bytes, or tuple):
                    If ``stream=True``, a generator yielding response chunks.
                    If ``socket=True``, a socket object for the connection.
                    If ``demux=True``, a tuple of two bytes: stdout and stderr.
                    A bytestring containing response data otherwise.

        Raises:
            APIError: If the server returns an error.
            MachineBinaryError: If the binary of the command is not found.
        """
        resp = self.client.api.exec_create(
            container.id, cmd, stdout=stdout, stderr=stderr, stdin=stdin, tty=tty,
            privileged=privileged, user=user, environment=environment,
            workdir=workdir,
        )

        try:
            exec_output = self.client.api.exec_start(
                resp['Id'], detach=detach, tty=tty, stream=stream, socket=socket, demux=demux
            )
        except APIError as e:
            matches = OCI_RUNTIME_RE.search(e.explanation)
            if matches:
                raise MachineBinaryError(matches.group(3) or matches.group(4), container.labels['name'])

            raise e

        exit_code = self.client.api.exec_inspect(resp['Id'])['ExitCode']
        if not socket and not stream and (exit_code is not None and exit_code != 0):
            (stdout_out, _) = exec_output if demux else (exec_output, None)
            exec_stdout = ""
            if stdout_out:
                if type(stdout_out) is bytes:
                    char_encoding = chardet.detect(stdout_out)
                    exec_stdout = stdout_out.decode(char_encoding['encoding'])
                else:
                    exec_stdout = stdout_out
            matches = OCI_RUNTIME_RE.search(exec_stdout)
            if matches:
                raise MachineBinaryError(matches.group(3) or matches.group(4), container.labels['name'])

        if socket or stream:
            return {'exit_code': None, 'output': exec_output}

        return {'exit_code': int(exit_code) if exit_code is not None else None, 'output': exec_output}

    def _wait_startup_execution(self, container: docker.models.containers.Container,
                                n_retries: Optional[int] = None, retry_interval: float = 1) -> bool:
        """Wait until the startup commands are executed or until the user requests the control over the device.

        Args:
            container (docker.models.containers.Container): The Docker container to wait.
            n_retries (Optional[int]): Number of retries before stopping waiting. Default is None, waits indefinitely.
            retry_interval (float): The time interval in seconds to wait for each retry. Default is 1.

        Returns:
            bool: False if the user requests the control before the ending of the startup. Else, True.
        """
        logging.debug(f"Waiting startup commands execution for device {container.labels['name']}...")

        n_retries = n_retries if n_retries is None or n_retries >= 0 else abs(n_retries)
        retry_interval = retry_interval if retry_interval >= 0 else 1

        retries = 0
        is_cmd_success = False
        startup_waited = True
        printed = False
        while not is_cmd_success:
            try:
                exec_result = self._exec_run(container,
                                             cmd="cat /tmp/EOS",
                                             stdout=True,
                                             stderr=False,
                                             privileged=False,
                                             detach=False
                                             )
                is_cmd_success = exec_result['exit_code'] == 0

                if not printed and not is_cmd_success:
                    EventDispatcher.get_instance().dispatch("machine_startup_wait_started")
                    printed = True

                # If the user requests the control, break the while loop
                if utils.exec_by_platform(utils.wait_user_input_linux,
                                          utils.wait_user_input_windows,
                                          utils.wait_user_input_linux):
                    startup_waited = False or is_cmd_success
                    break

                if not is_cmd_success:
                    if n_retries is not None:
                        if retries == n_retries:
                            break
                        retries += 1

                    time.sleep(retry_interval)
            except KeyboardInterrupt:
                # Disable the CTRL+C interrupt while waiting for startup, otherwise terminal will close.
                pass

        return startup_waited

    @staticmethod
    def copy_files(machine_api_object: docker.models.containers.Container, path: str, tar_data: bytes) -> None:
        """Copy the files contained in tar_data in the Docker container path specified by the machine_api_object.

        Args:
            machine_api_object (docker.models.containers.Container): A Docker container.
            path (str): The path of the container where copy the tar_data.
            tar_data (bytes): The data to copy in the container.

        Returns:
            None
        """
        machine_api_object.put_archive(path, tar_data)

    def get_machines_api_objects_by_filters(self, lab_hash: str = None, machine_name: str = None, user: str = None) -> \
            List[docker.models.containers.Container]:
        """Return the Docker containers objects specified by lab_hash and user.

        Args:
            lab_hash (str): The hash of a network scenario. If specified, return all the devices in the scenario.
            machine_name (str): The name of a device. If specified, return the specified container of the scenario.
            user (str): The name of a user on the host. If specified, return only the containers of the user.

        Returns:
            List[docker.models.containers.Container]: A list of Docker containers objects.
        """
        filters = {"label": ["app=kathara"]}
        if user:
            filters["label"].append(f"user={user}")
        if lab_hash:
            filters["label"].append(f"lab_hash={lab_hash}")
        if machine_name:
            filters["label"].append(f"name={machine_name}")

        return self.client.containers.list(all=True, filters=filters, ignore_removed=True)

    def get_machines_stats(self, lab_hash: str = None, machine_name: str = None, user: str = None) -> \
            Generator[Dict[str, DockerMachineStats], None, None]:
        """Return a generator containing the Docker devices' stats.

        Args:
            lab_hash (str): The hash of a network scenario. If specified, return all the stats of the devices in the
                scenario.
            machine_name (str): The name of a device. If specified, return the specified device stats.
            user (str): The name of a user on the host. If specified, return only the stats of the specified user.

        Returns:
            Generator[Dict[str, DockerMachineStats], None, None]: A generator containing device names as keys and
            DockerMachineStats as values.

        Raises:
            PrivilegeError: If user param is None and the user does not have root privileges.
        """
        if user is None and not utils.is_admin():
            raise PrivilegeError("You must be root to get devices statistics of all users.")

        machines_stats = {}

        def load_machine_stats(machine):
            if machine.name not in machines_stats:
                machines_stats[machine.name] = DockerMachineStats(machine)

        while True:
            containers = self.get_machines_api_objects_by_filters(
                lab_hash=lab_hash, machine_name=machine_name, user=user
            )
            if not containers:
                yield dict()

            pool_size = utils.get_pool_size()
            items = utils.chunk_list(containers, pool_size)
            with Pool(pool_size) as machines_pool:
                for chunk in items:
                    machines_pool.map(func=load_machine_stats, iterable=chunk)

            machines_to_remove = []
            for machine_id, machine_stats in machines_stats.items():
                try:
                    machine_stats.update()
                except StopIteration:
                    machines_to_remove.append(machine_id)
                    continue

            for k in machines_to_remove:
                machines_stats.pop(k, None)

            yield machines_stats

    @staticmethod
    def get_container_name(name: str, lab_hash: str) -> str:
        """Return the name of a Docker container.

        Args:
            name (str): The name of a Kathara device.
            lab_hash (str): The hash of a running scenario.

        Returns:
            str: The name of the Docker container in the format "|dev_prefix|_|username_prefix|_|name|_|lab_hash|".
        """
        lab_hash = lab_hash if "_%s" % lab_hash else ""
        return "%s_%s_%s_%s" % (Setting.get_instance().device_prefix, utils.get_current_user_name(), name, lab_hash)

    def _delete_machine(self, container: docker.models.containers.Container) -> None:
        """Remove a running Docker container.

        Args:
            container (docker.models.containers.Container): The Docker container to remove.

        Returns:
            None
        """
        # Build the shutdown command string
        shutdown_commands_string = "; ".join(SHUTDOWN_COMMANDS).format(machine_name=container.labels["name"])

        logging.debug(f"Executing shutdown commands on `{container.labels['name']}`: {shutdown_commands_string}")
        # Execute the shutdown commands inside the container (only if it's running)
        if container.status == "running":
            try:
                self._exec_run(container,
                               cmd=[container.labels['shell'], '-c', shutdown_commands_string],
                               stdout=True,
                               stderr=False,
                               privileged=True,
                               detach=False
                               )
            except MachineBinaryError as e:
                logging.warning(f"Shell `{e.binary}` not found in "
                                f"image `{container.image.tags[0]}` of device `{container.labels['name']}`. "
                                f"Shutdown commands will not be executed."
                                )

        container.remove(v=True, force=True)
