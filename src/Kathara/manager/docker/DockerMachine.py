import logging
import re
import shlex
import sys
import time
from itertools import islice
from multiprocessing.dummy import Pool
from typing import List, Dict, Generator, Optional, Set, Tuple, Union, Any

import docker.models.containers
from docker import DockerClient
from docker.errors import APIError

from .DockerImage import DockerImage
from .stats.DockerMachineStats import DockerMachineStats
from ... import utils
from ...event.EventDispatcher import EventDispatcher
from ...exceptions import MountDeniedError, MachineAlreadyExistsError, MachineNotFoundError, DockerPluginError, \
    MachineBinaryError
from ...model.Lab import Lab
from ...model.Link import Link, BRIDGE_LINK_NAME
from ...model.Machine import Machine, MACHINE_CAPABILITIES
from ...setting.Setting import Setting

RP_FILTER_NAMESPACE = "net.ipv4.conf.%s.rp_filter"
OCI_RUNTIME_RE = re.compile(
    r"OCI runtime exec failed(.*?)(stat (.*): no such file or directory|exec: \"(.*)\": executable file not found)"
)

# Known commands that each container should execute
# Run order: shared.startup, machine.startup and machine.meta['startup_commands']
STARTUP_COMMANDS = [
    # Unmount the /etc/resolv.conf and /etc/hosts files, automatically mounted by Docker inside the container.
    # In this way, they can be overwritten by custom user files.
    "umount /etc/resolv.conf",
    "umount /etc/hosts",

    # Copy the machine folder (if present) from the hostlab directory into the root folder of the container
    # In this way, files are all replaced in the container root folder
    "if [ -d \"/hostlab/{machine_name}\" ]; then "
    "(cd /hostlab/{machine_name} && tar c .) | (cd / && tar xhf -); fi",

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
    "chown quagga:quagga /etc/quagga/*",
    "chmod 640 /etc/quagga/*; fi",

    # Give proper permissions to FRR files (if present)
    "if [ -d \"/etc/frr\" ]; then "
    "chown frr:frr /etc/frr/*",
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

    "touch /var/log/EOS"
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
    __slots__ = ['client', 'docker_image']

    def __init__(self, client: DockerClient, docker_image: DockerImage) -> None:
        self.client: DockerClient = client

        self.docker_image: DockerImage = docker_image

    def deploy_machines(self, lab: Lab, selected_machines: Set[str] = None) -> None:
        """Deploy all the network scenario devices as Docker containers.

        Args:
            lab (Kathara.model.Lab.Lab): A Kathara network scenario.
            selected_machines (Set[str]): A set containing the name of the devices to deploy.

        Returns:
            None
        """
        machines = {k: v for (k, v) in lab.machines.items() if k in selected_machines}.items() if selected_machines \
            else lab.machines.items()

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
            machines_pool = Pool(pool_size)

            items = utils.chunk_list(machines, pool_size)

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

        ports_info = machine.get_ports()
        ports = None
        if ports_info:
            ports = {}
            for (host_port, protocol), guest_port in ports_info.items():
                ports['%d/%s' % (guest_port, protocol)] = host_port

        # Get the general options into a local variable (just to avoid accessing the lab object every time)
        options = machine.lab.general_options

        # If bridged is required in command line but not defined in machine meta, add it.
        if "bridged" in options and not machine.meta['bridged']:
            machine.add_meta("bridged", True)

        if ports and not machine.meta['bridged']:
            logging.warning(
                "To expose ports of device `%s` on the host, "
                "you have to specify the `bridged` option on that device." % machine.name
            )

        # If any exec command is passed in command line, add it.
        if "exec" in options:
            machine.add_meta("exec", options["exec"])

        # Get the first network object, if defined.
        # This should be used in container create function
        first_network = None
        if machine.interfaces:
            first_network = machine.interfaces[0].api_object

        # If no interfaces are declared in machine, but bridged mode is required, get bridge as first link.
        # Flag that bridged is already connected (because there's another check in `start`).
        if first_network is None and machine.meta['bridged']:
            first_network = machine.lab.get_or_new_link(BRIDGE_LINK_NAME).api_object
            machine.add_meta("bridge_connected", True)

        # Sysctl params to pass to the container creation
        sysctl_parameters = {RP_FILTER_NAMESPACE % x: 0 for x in ["all", "default", "lo"]}

        if first_network:
            sysctl_parameters[RP_FILTER_NAMESPACE % "eth0"] = 0

        sysctl_parameters["net.ipv4.ip_forward"] = 1
        sysctl_parameters["net.ipv4.icmp_ratelimit"] = 0

        if machine.is_ipv6_enabled():
            sysctl_parameters["net.ipv6.conf.all.forwarding"] = 1
            sysctl_parameters["net.ipv6.icmp.ratelimit"] = 0
            sysctl_parameters["net.ipv6.conf.default.disable_ipv6"] = 0
            sysctl_parameters["net.ipv6.conf.all.disable_ipv6"] = 0

        # Merge machine sysctls
        sysctl_parameters = {**sysctl_parameters, **machine.meta['sysctls']}

        volumes = {}

        shared_mount = options['shared_mount'] if 'shared_mount' in options else Setting.get_instance().shared_mount
        if shared_mount and machine.lab.shared_path:
            volumes[machine.lab.shared_path] = {'bind': '/shared', 'mode': 'rw'}

        # Mount the host home only if specified in settings.
        hosthome_mount = options['hosthome_mount'] if 'hosthome_mount' in options else \
            Setting.get_instance().hosthome_mount
        if hosthome_mount and Setting.get_instance().remote_url is None:
            volumes[utils.get_current_user_home()] = {'bind': '/hosthome', 'mode': 'rw'}

        privileged = options['privileged_machines'] if 'privileged_machines' in options else False
        if Setting.get_instance().remote_url is not None and privileged:
            privileged = False
            logging.warning("Privileged flag is ignored with a remote Docker connection.")

        container_name = self.get_container_name(machine.name, machine.lab.hash)

        try:
            machine_container = self.client.containers.create(image=image,
                                                              name=container_name,
                                                              hostname=machine.name,
                                                              cap_add=MACHINE_CAPABILITIES if not privileged else None,
                                                              privileged=privileged,
                                                              network=first_network.name if first_network else None,
                                                              network_mode="bridge" if first_network else "none",
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
                                                                      }
                                                              )
        except APIError as e:
            raise e

        # Pack machine files into a tar.gz and extract its content inside `/`
        tar_data = machine.pack_data()
        if tar_data:
            self.copy_files(machine_container, "/", tar_data)

        machine.api_object = machine_container

    @staticmethod
    def connect_to_link(machine: Machine, link: Link) -> None:
        """Connect the Docker container representing the machine to a specified collision domain.

        Args:
            machine (Kathara.model.Machine): A Kathara device.
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None

        Raises:
            DockerPluginError: If Kathara has been left in an inconsistent state.
            APIError: If the Docker APIs return an error.
        """
        attached_networks = machine.api_object.attrs["NetworkSettings"]["Networks"]

        if link.api_object.name not in attached_networks:
            try:
                link.api_object.connect(machine.api_object)
            except APIError as e:
                if e.response.status_code == 500 and \
                        ("network does not exist" in e.explanation or "endpoint does not exist" in e.explanation):
                    raise DockerPluginError(
                        "Kathara has been left in an inconsistent state! Please run `kathara wipe`.")
                else:
                    raise e

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
        for (iface_num, machine_link) in islice(machine.interfaces.items(), 1, None):
            logging.debug("Connecting device `%s` to collision domain `%s` on interface %d..." % (machine.name,
                                                                                                  machine_link.name,
                                                                                                  iface_num
                                                                                                  )
                          )
            try:
                machine_link.api_object.connect(machine.api_object)
            except APIError as e:
                if e.response.status_code == 500 and \
                        ("network does not exist" in e.explanation or "endpoint does not exist" in e.explanation):
                    raise DockerPluginError(
                        "Kathara has been left in an inconsistent state! Please run `kathara wipe`.")
                else:
                    raise e

        # Bridged connection required but not added in `deploy` method.
        if "bridge_connected" not in machine.meta and machine.meta['bridged']:
            bridge_link = machine.lab.get_or_new_link(BRIDGE_LINK_NAME).api_object
            bridge_link.connect(machine.api_object)

        # Append executed machine startup commands inside the /var/log/startup.log file
        if machine.meta['startup_commands']:
            new_commands = []
            for command in machine.meta['startup_commands']:
                new_commands.append("echo \"++ %s\" &>> /var/log/startup.log" % command)
                new_commands.append(command)
            machine.meta['startup_commands'] = new_commands

        # Build the final startup commands string
        startup_commands_string = "; ".join(
            STARTUP_COMMANDS if machine.meta['startup_commands'] else STARTUP_COMMANDS[:-2] + STARTUP_COMMANDS[-1:]
        ).format(
            machine_name=machine.name,
            machine_commands="; ".join(machine.meta['startup_commands'])
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

    def undeploy(self, lab_hash: str, selected_machines: Set[str] = None) -> None:
        """Undeploy the devices contained in the network scenario defined by the lab_hash.

        If a set of selected_machines is specified, undeploy only the specified devices.

        Args:
            lab_hash (str): The hash of the network scenario to undeploy.
            selected_machines (Optional[Set[str]]): If not None, undeploy only the specified devices.

        Returns:
            None
        """
        containers = self.get_machines_api_objects_by_filters(lab_hash=lab_hash, user=utils.get_current_user_name())

        if selected_machines is not None and len(selected_machines) > 0:
            containers = [item for item in containers if item.labels["name"] in selected_machines]

        if len(containers) > 0:
            pool_size = utils.get_pool_size()
            machines_pool = Pool(pool_size)

            items = utils.chunk_list(containers, pool_size)

            EventDispatcher.get_instance().dispatch("machines_undeploy_started", items=containers)

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
        machines_pool = Pool(pool_size)

        items = utils.chunk_list(containers, pool_size)

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
                logs: bool = False, wait: bool = True) -> None:
        """Open a stream to the Docker container specified by machine_name using the specified shell.

        Args:
            lab_hash (str): The hash of the network scenario containing the device.
            machine_name (str): The name of the device to connect.
            user (str): The name of a current user on the host.
            shell (str): The path to the desired shell.
            logs (bool): If True, print the logs of the startup command.
            wait (bool): If True, wait the end of the startup commands before giving control to the user.

        Returns:
            None

        Raises:
            MachineNotFoundError: If the specified device is not running.
        """
        containers = self.get_machines_api_objects_by_filters(lab_hash=lab_hash, machine_name=machine_name, user=user)
        if not containers:
            raise MachineNotFoundError("The specified device `%s` is not running." % machine_name)
        container = containers.pop()

        if not shell:
            shell = shlex.split(container.labels['shell'])
        else:
            shell = shlex.split(shell)

        logging.debug(f"Connect to device `{machine_name}` with shell: {shell}")

        def wait_user_input_linux():
            import select
            to_break, _, _ = select.select([sys.stdin], [], [], 0.1)
            return to_break

        def wait_user_input_windows():
            import msvcrt
            return msvcrt.kbhit()

        startup_waited = True
        if wait:
            logging.debug(f"Waiting startup commands execution for device {machine_name}")
            exit_code = 1
            while exit_code != 0:
                exec_result = self._exec_run(container,
                                             cmd="cat /var/log/EOS",
                                             stdout=True,
                                             stderr=False,
                                             privileged=False,
                                             detach=False
                                             )
                exit_code = exec_result['exit_code']

                sys.stdout.write("\033[2J")
                sys.stdout.write("\033[0;0H")
                sys.stdout.write("Waiting startup commands execution. Press enter to take control of the device...")
                sys.stdout.flush()

                if utils.exec_by_platform(wait_user_input_linux, wait_user_input_windows, wait_user_input_linux):
                    startup_waited = False
                    break

                time.sleep(0.1)

        sys.stdout.write("\033[2J")
        sys.stdout.write("\033[0;0H")
        sys.stdout.flush()

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
        startup_output = exec_result['output'].decode('utf-8')

        if startup_output and logs and Setting.get_instance().print_startup_log:
            print("--- Startup Commands Log\n")
            print(startup_output)
            print("--- End Startup Commands Log\n" if startup_waited
                  else "--- Executing Other Commands in Background\n")

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
             tty: bool = True) -> Generator[Tuple[bytes, bytes], None, None]:
        """Execute the command on the Docker container specified by the lab_hash and the machine_name.

        Args:
            lab_hash (str): The hash of the network scenario containing the device.
            machine_name (str): The name of the device.
            user (str): The name of a current user on the host.
            command (Union[str, List]): The command to execute.
            tty (bool): If True, open a new tty.

        Returns:
            Generator[Tuple[bytes, bytes]]: A generator of tuples containing the stdout and stderr in bytes.

        Raises:
            MachineNotFoundError: If the specified device is not running.
        """
        logging.debug("Executing command `%s` to device with name: %s" % (command, machine_name))

        containers = self.get_machines_api_objects_by_filters(lab_hash=lab_hash, machine_name=machine_name, user=user)
        if not containers:
            raise MachineNotFoundError("The specified device `%s` is not running." % machine_name)
        container = containers.pop()

        command = shlex.split(command) if type(command) == str else command
        exec_result = self._exec_run(container,
                                     cmd=command,
                                     stdout=True,
                                     stderr=True,
                                     tty=tty,
                                     privileged=False,
                                     stream=True,
                                     demux=True,
                                     detach=False
                                     )

        return exec_result['output']

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
            exec_stdout = (stdout_out.decode('utf-8') if type(stdout_out) == bytes else stdout_out) if stdout else ""
            matches = OCI_RUNTIME_RE.search(exec_stdout)
            if matches:
                raise MachineBinaryError(matches.group(3) or matches.group(4), container.labels['name'])

        if socket or stream:
            return {'exit_code': None, 'output': exec_output}

        return {'exit_code': int(exit_code) if exit_code is not None else None, 'output': exec_output}

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
            filters["label"].append("user=%s" % user)
        if lab_hash:
            filters["label"].append("lab_hash=%s" % lab_hash)
        if machine_name:
            filters["label"].append("name=%s" % machine_name)

        return self.client.containers.list(all=True, filters=filters)

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
            MachineNotFoundError: If the specified devices are not running.
        """
        containers = self.get_machines_api_objects_by_filters(lab_hash=lab_hash, machine_name=machine_name, user=user)
        if not containers:
            if not machine_name:
                raise MachineNotFoundError("No devices found.")
            else:
                raise MachineNotFoundError(f"Devices with name {machine_name} not found.")

        containers = sorted(containers, key=lambda x: x.name)

        machine_streams = {}

        for machine in containers:
            machine_streams[machine.name] = DockerMachineStats(machine)

        while True:
            for machine_stats in machine_streams.values():
                try:
                    machine_stats.update()
                except StopIteration:
                    continue

            yield machine_streams

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

        # Execute the shutdown commands inside the container (only if it's running)
        if container.status == "running":
            try:
                self._exec_run(container,
                               cmd=[container.labels['shell'], '-c', shutdown_commands_string],
                               stdout=False,
                               stderr=False,
                               privileged=True,
                               detach=True
                               )
            except MachineBinaryError as e:
                logging.warning(f"Shell `{e.binary}` not found in "
                                f"image `{container.image.tags[0]}` of device `{container.labels['name']}`. "
                                f"Shutdown commands will not be executed."
                                )

        container.remove(force=True)
