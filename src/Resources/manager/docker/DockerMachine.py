import logging
import shlex
from functools import partial
from itertools import islice
from multiprocessing.dummy import Pool

import progressbar
from docker.errors import APIError

from ... import utils
from ...exceptions import MountDeniedError, MachineAlreadyExistsError
from ...model.Link import BRIDGE_LINK_NAME
from ...setting.Setting import Setting

RP_FILTER_NAMESPACE = "net.ipv4.conf.%s.rp_filter"

# Known commands that each container should execute
# Run order: shared.startup, machine.startup and machine.startup_commands
STARTUP_COMMANDS = [
    # Copy the machine folder (if present) from the hostlab directory into the root folder of the container
    # In this way, files are all replaced in the container root folder
    "if [ -d \"/hostlab/{machine_name}\" ]; then "
    "(cd /hostlab/{machine_name} && tar c .) | (cd / && tar xhf -); fi",

    # Patch the /etc/resolv.conf file. If present, replace the content with the one of the machine.
    # If not, clear the content of the file.
    # This should be patched with "cat" because file is already in use by Docker internal DNS.
    "if [ -f \"/hostlab/{machine_name}/etc/resolv.conf\" ]; then "
    "cat /hostlab/{machine_name}/etc/resolv.conf > /etc/resolv.conf; else "
    "echo \"\" > /etc/resolv.conf; fi",

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
    "{machine_commands}"
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
    __slots__ = ['client', 'docker_image']

    def __init__(self, client, docker_image):
        self.client = client

        self.docker_image = docker_image

    def deploy_machines(self, lab):
        # Check and pulling machine images
        lab_images = set(map(lambda x: x.get_image(), lab.machines.values()))
        self.docker_image.check_and_pull_from_list(lab_images)

        shared_mount = lab.general_options['shared_mount'] if 'shared_mount' in lab.general_options \
            else Setting.get_instance().shared_mount

        if shared_mount:
            lab.create_shared_folder()

        machines = lab.machines.items()

        progress_bar = None
        if utils.CLI_ENV:
            progress_bar = progressbar.ProgressBar(
                widgets=['Deploying devices... ', progressbar.Bar(),
                         ' ', progressbar.Counter(format='%(value)d/%(max_value)d')],
                redirect_stdout=True,
                max_value=len(machines)
            )

        # Deploy all lab machines.
        # If there is no lab.dep file, machines can be deployed using multithreading.
        # If not, they're started sequentially
        if not lab.has_dependencies:
            pool_size = utils.get_pool_size()
            machines_pool = Pool(pool_size)

            items = utils.chunk_list(machines, pool_size)

            for chunk in items:
                machines_pool.map(func=partial(self._deploy_and_start_machine, progress_bar), iterable=chunk)
        else:
            for item in machines:
                self._deploy_and_start_machine(progress_bar, item)

        if utils.CLI_ENV:
            progress_bar.finish()

    def _deploy_and_start_machine(self, progress_bar, machine_item):
        (_, machine) = machine_item

        self.create(machine)
        self.start(machine)

        if progress_bar is not None:
            progress_bar += 1

    def create(self, machine):
        logging.debug("Creating device `%s`..." % machine.name)

        image = machine.get_image()
        memory = machine.get_mem()
        cpus = machine.get_cpu(multiplier=1e9)

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

        shared_mount = options['shared_mount'] if 'shared_mount' in options else machine.meta['shared_mount']
        if shared_mount and machine.lab.shared_folder:
            volumes = {machine.lab.shared_folder: {'bind': '/shared', 'mode': 'rw'}}

        # Mount the host home only if specified in settings.
        hosthome_mount = options['hosthome_mount'] if 'hosthome_mount' in options else machine.meta['hosthome_mount']
        if hosthome_mount:
            volumes[utils.get_current_user_home()] = {'bind': '/hosthome', 'mode': 'rw'}

        privileged = options['privileged_machines'] if 'privileged_machines' in options else machine.meta['privileged']

        container_name = self.get_container_name(machine.name, machine.lab.folder_hash)
        try:
            machine_container = self.client.containers.create(image=image,
                                                              name=container_name,
                                                              hostname=machine.name,
                                                              cap_add=machine.capabilities if not privileged else None,
                                                              privileged=privileged,
                                                              network=first_network.name if first_network else None,
                                                              network_mode="bridge" if first_network else "none",
                                                              sysctls=sysctl_parameters,
                                                              mem_limit=memory,
                                                              nano_cpus=cpus,
                                                              ports=ports,
                                                              tty=True,
                                                              stdin_open=True,
                                                              detach=True,
                                                              volumes=volumes,
                                                              labels={"name": machine.name,
                                                                      "lab_hash": machine.lab.folder_hash,
                                                                      "user": utils.get_current_user_name(),
                                                                      "app": "kathara",
                                                                      "shell": machine.meta["shell"]
                                                                      if "shell" in machine.meta
                                                                      else Setting.get_instance().device_shell
                                                                      }
                                                              )
        except APIError as e:
            if e.response.status_code == 409 and e.explanation.startswith('Conflict.'):
                raise MachineAlreadyExistsError("Device with name `%s` already exists." % machine.name)
            else:
                raise e

        # Pack machine files into a tar.gz and extract its content inside `/`
        tar_data = machine.pack_data()
        if tar_data:
            self.copy_files(machine_container, "/", tar_data)

        machine.api_object = machine_container

    def update(self, machine):
        machines = self.get_machines_by_filters(machine_name=machine.name, lab_hash=machine.lab.folder_hash)

        if not machines:
            raise Exception("Device `%s` not found." % machine.name)

        machine.api_object = machines.pop()
        attached_networks = machine.api_object.attrs["NetworkSettings"]["Networks"]

        # Connect the container to its new networks
        for (_, machine_link) in machine.interfaces.items():
            if machine_link.api_object.name not in attached_networks:
                machine_link.api_object.connect(machine.api_object)

    @staticmethod
    def start(machine):
        logging.debug("Starting device `%s`..." % machine.name)

        try:
            machine.api_object.start()
        except APIError as e:
            if e.response.status_code == 500 and e.explanation.startswith('Mounts denied'):
                raise MountDeniedError("Host drive is not shared with Docker.")
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

            machine_link.api_object.connect(machine.api_object)

        # Bridged connection required but not added in `deploy` method.
        if "bridge_connected" not in machine.meta and machine.meta['bridged']:
            bridge_link = machine.lab.get_or_new_link(BRIDGE_LINK_NAME).api_object
            bridge_link.connect(machine.api_object)

        # Build the final startup commands string
        startup_commands_string = "; ".join(STARTUP_COMMANDS).format(
            machine_name=machine.name,
            machine_commands="; ".join(machine.startup_commands)
        )

        # Execute the startup commands inside the container (without privileged flag so basic permissions are used)
        machine.api_object.exec_run(cmd=[Setting.get_instance().device_shell, '-c', startup_commands_string],
                                    stdout=False,
                                    stderr=False,
                                    privileged=False,
                                    detach=True
                                    )

        if Setting.get_instance().open_terminals:
            for i in range(0, machine.get_num_terms()):
                machine.connect(Setting.get_instance().terminal)

    def undeploy(self, lab_hash, selected_machines=None):
        machines = self.get_machines_by_filters(lab_hash=lab_hash)
        if selected_machines is not None and len(selected_machines) > 0:
            machines = [item for item in machines if item.labels["name"] in selected_machines]

        if len(machines) > 0:
            pool_size = utils.get_pool_size()
            machines_pool = Pool(pool_size)

            items = utils.chunk_list(machines, pool_size)

            progress_bar = None
            if utils.CLI_ENV:
                progress_bar = progressbar.ProgressBar(
                    widgets=['Deleting devices... ', progressbar.Bar(),
                             ' ', progressbar.Counter(format='%(value)d/%(max_value)d')],
                    redirect_stdout=True,
                    max_value=len(machines)
                )

            for chunk in items:
                machines_pool.map(func=partial(self._undeploy_machine, progress_bar),
                                  iterable=chunk
                                  )
            if utils.CLI_ENV:
                progress_bar.finish()

    def wipe(self, user=None):
        machines = self.get_machines_by_filters(user=user)

        pool_size = utils.get_pool_size()
        machines_pool = Pool(pool_size)

        items = utils.chunk_list(machines, pool_size)

        for chunk in items:
            machines_pool.map(func=partial(self._undeploy_machine, None), iterable=chunk)

    def _undeploy_machine(self, progress_bar, machine_item):
        self.delete_machine(machine_item)

        if progress_bar is not None:
            progress_bar += 1

    def connect(self, lab_hash, machine_name, shell=None, logs=False):
        container = self.get_machine(lab_hash=lab_hash, machine_name=machine_name)

        if not shell:
            shell = shlex.split(container.labels['shell'])
        else:
            shell = shlex.split(shell) if type(shell) == str else shell

        logging.debug("Connect to device `%s` with shell: %s" % (machine_name, shell))

        if logs and Setting.get_instance().print_startup_log:
            (result_string, _) = self.exec(lab_hash,
                                           machine_name,
                                           command="cat /var/log/shared.log /var/log/startup.log",
                                           tty=False
                                           )

            if result_string:
                print("--- Startup Commands Log\n")
                print(result_string)
                print("--- End Startup Commands Log\n")

        container = self.get_machine(lab_hash=lab_hash, machine_name=machine_name)

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

    def exec(self, lab_hash, machine_name, command, tty=True):
        logging.debug("Executing command `%s` to device with name: %s" % (command, machine_name))

        container = self.get_machine(lab_hash, machine_name)

        (exit_code, (stdout, stderr)) = container.exec_run(cmd=command,
                                                           stdout=True,
                                                           stderr=True,
                                                           tty=tty,
                                                           privileged=False,
                                                           demux=True,
                                                           detach=False
                                                           )

        return stdout.decode('utf-8') if stdout else "", stderr.decode('utf-8') if stderr else ""

    @staticmethod
    def copy_files(machine, path, tar_data):
        machine.put_archive(path, tar_data)

    def get_machines_by_filters(self, lab_hash=None, machine_name=None, user=None):
        filters = {"label": ["app=kathara"]}
        if user:
            filters["label"].append("user=%s" % user)
        if lab_hash:
            filters["label"].append("lab_hash=%s" % lab_hash)
        if machine_name:
            filters["label"].append("name=%s" % machine_name)

        return self.client.containers.list(all=True, filters=filters)

    def get_machine(self, lab_hash, machine_name):
        logging.debug("Searching container `%s` with lab hash `%s`" % (machine_name, lab_hash))

        containers = self.get_machines_by_filters(lab_hash=lab_hash, machine_name=machine_name)

        logging.debug("Found containers: %s" % str(containers))

        if len(containers) != 1:
            raise Exception("Error getting the device `%s` inside the lab." % machine_name)
        else:
            return containers[0]

    def get_machine_info(self, machine_name, lab_hash=None, user=None):
        machines = self.get_machines_by_filters(machine_name=machine_name, lab_hash=lab_hash, user=user)

        if not machines:
            raise Exception("The specified device '%s' is not running." % machine_name)
        elif len(machines) > 1:
            raise Exception("There is more than one device matching the name `%s`." % machine_name)

        machine = machines[0]
        machine_stats = machine.stats(stream=False)

        return self._get_stats_by_machine(machine, machine_stats)

    def get_machines_info(self, lab_hash, machine_filter=None, user=None):
        machines = self.get_machines_by_filters(lab_hash=lab_hash, machine_name=machine_filter, user=user)

        if not machines:
            if not lab_hash:
                raise Exception("No devices running.")
            else:
                raise Exception("Lab is not started.")

        machines = sorted(machines, key=lambda x: x.name)

        machine_streams = {}

        for machine in machines:
            machine_streams[machine] = machine.stats(stream=True, decode=True)

        while True:
            machines_data = []

            for (machine, machine_stats) in machine_streams.items():
                try:
                    result = next(machine_stats)
                except StopIteration:
                    continue

                machines_data.append(self._get_stats_by_machine(machine, result))

            yield machines_data

    def _get_stats_by_machine(self, machine, machine_stats):
        stats = self._get_aggregate_machine_info(machine_stats)

        return {
            "real_lab_hash": machine.labels['lab_hash'],
            "name": machine.labels['name'],
            "real_name": machine.name,
            "user": machine.labels['user'],
            "status": machine.status,
            "image": machine.image.tags[0],
            "pids": machine_stats['pids_stats']['current'] if 'current' in machine_stats['pids_stats'] else 0,
            "cpu_usage": stats['cpu_usage'],
            "mem_usage": stats['mem_usage'],
            "mem_percent": stats['mem_percent'],
            "net_usage": stats['net_usage']
        }

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

    @staticmethod
    def get_container_name(name, lab_hash):
        lab_hash = lab_hash if lab_hash else ""
        return "%s_%s_%s_%s" % (Setting.get_instance().device_prefix, utils.get_current_user_name(), name, lab_hash)

    @staticmethod
    def delete_machine(machine):
        # Build the shutdown command string
        shutdown_commands_string = "; ".join(SHUTDOWN_COMMANDS).format(machine_name=machine.labels["name"])

        # Execute the shutdown commands inside the container (only if it's running)
        if machine.status == "running":
            machine.exec_run(cmd=[Setting.get_instance().device_shell, '-c', shutdown_commands_string],
                             stdout=False,
                             stderr=False,
                             privileged=True,
                             detach=True
                             )

        machine.remove(force=True)
