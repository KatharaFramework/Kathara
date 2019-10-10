import logging
from itertools import islice
from subprocess import Popen

from docker.errors import APIError

from ... import utils
from ...exceptions import MountDeniedError, MachineAlreadyExistsError
from ...setting.Setting import Setting

RP_FILTER_NAMESPACE = "net.ipv4.conf.%s.rp_filter"
SYSCTL_COMMAND = "sysctl %s=0" % RP_FILTER_NAMESPACE

# Known commands that each container should execute
# Run order: rp_filters, shared.startup, machine.startup and machine.startup_commands
STARTUP_COMMANDS = [
    # Copy the machine folder (if present) from the hostlab directory into the root folder of the container
    # In this way, files are all replaced in the container root folder
    # rsync is used to keep symlinks while copying files.
    "if [ -d \"/hostlab/{machine_name}\" ]; then "
    "chmod -R 777 /hostlab/{machine_name}/*; "
    "rsync -r -K /hostlab/{machine_name}/* /; fi",

    # Give proper permissions to /var/www
    "chmod -R 777 /var/www/*",

    # Placeholder for rp_filter patches
    "{rp_filter}",

    # If shared.startup file is present
    "if [ -f \"/hostlab/shared.startup\" ]; then "
    # Give execute permissions to the file and execute it
    # We redirect the output "&>" to a debugging file
    "chmod u+x /hostlab/shared.startup; /hostlab/shared.startup &> /var/log/shared.log; fi",

    # If .startup file is present
    "if [ -f \"/hostlab/{machine_name}.startup\" ]; then "
    # Give execute permissions to the file and execute it
    # We redirect the output "&>" to a debugging file
    "chmod u+x /hostlab/{machine_name}.startup; "
    "/hostlab/{machine_name}.startup &> /var/log/startup.log; fi",

    # Placeholder for user commands
    "{machine_commands}"
]

SHUTDOWN_COMMANDS = [
    # If shared.shutdown file is present
    "if [ -f \"/hostlab/shared.shutdown\" ]; then "
    # Give execute permissions to the file and execute it
    "chmod u+x /hostlab/shared.shutdown; /hostlab/shared.shutdown; fi",

    # If machine.shutdown file is present
    "if [ -f \"/hostlab/{machine_name}.shutdown\" ]; then "
    # Give execute permissions to the file and execute it
    "chmod u+x /hostlab/{machine_name}.shutdown; /hostlab/{machine_name}.shutdown; fi",
]


class DockerMachine(object):
    __slots__ = ['client', 'docker_image']

    def __init__(self, client, docker_image):
        self.client = client

        self.docker_image = docker_image

    def deploy(self, machine):
        # Get the general options into a local variable (just to avoid accessing the lab object every time)
        options = machine.lab.general_options

        # Container image, if defined in machine meta. If not use default one.
        image = options["image"] if "image" in options else machine.meta["image"] if "image" in machine.meta \
                else Setting.get_instance().image
        # Memory limit, if defined in machine meta.
        memory = options["mem"].upper() if "mem" in options else machine.meta["mem"].upper() if "mem" in machine.meta \
                 else None
        # Bind the port 3000 of the container to a defined port (if present).
        ports = None
        if "port" in options:
            try:
                ports = {'3000/tcp': int(options["port"])}
            except ValueError:
                pass
        elif "port" in machine.meta:
            try:
                ports = {'3000/tcp': int(machine.meta["port"])}
            except ValueError:
                pass

        # If bridged is required in command line, add it.
        if "bridged" in options:
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
        # Flag that bridged is already connected (because there's another check below).
        bridged_connected = False
        if first_network is None and machine.bridge:
            first_network = machine.bridge.api_object
            bridged_connected = True

        # Sysctl params to pass to the container creation
        sysctl_parameters = {RP_FILTER_NAMESPACE % x: 0 for x in ["all", "default", "lo"]}
        sysctl_parameters["net.ipv4.ip_forward"] = 1
        # TODO: ipv6_forward not found?
        # sysctl_parameters["net.ipv6.ip_forward"] = 1

        volumes = {}

        if machine.lab.shared_folder:
            volumes = {machine.lab.shared_folder: {'bind': '/shared', 'mode': 'rw'}}

        # Mount the host home only if specified in settings.
        if Setting.get_instance().hosthome_mount:
            volumes[utils.get_current_user_home()] = {'bind': '/hosthome', 'mode': 'rw'}

        try:
            self.docker_image.check_and_pull(image)
        except Exception as e:
            raise Exception(str(e))

        container_name = self.get_container_name(machine.name, machine.lab.folder_hash)
        try:
            machine_container = self.client.containers.create(image=image,
                                                              name=container_name,
                                                              hostname=machine.name,
                                                              privileged=True,
                                                              network=first_network.name if first_network else None,
                                                              network_mode="bridge" if first_network else "none",
                                                              sysctls=sysctl_parameters,
                                                              mem_limit=memory,
                                                              ports=ports,
                                                              tty=True,
                                                              stdin_open=True,
                                                              detach=True,
                                                              volumes=volumes,
                                                              labels={"name": machine.name,
                                                                      "lab_hash": machine.lab.folder_hash,
                                                                      "user": utils.get_current_user_name(),
                                                                      "app": "kathara"
                                                                      }
                                                              )
        except APIError as e:
            if e.response.status_code == 409 and e.explanation.startswith('Conflict.'):
                raise MachineAlreadyExistsError("Machine with name `%s` already exists." % machine.name)
            else:
                raise e

        # Pack machine files into a tar.gz and extract its content inside `/`
        tar_data = machine.pack_data()
        if tar_data:
            machine_container.put_archive("/", tar_data)

        # Build sysctl rp_filter commands for interfaces (since eth0 is connected above, we already put it here)
        rp_filter_commands = [SYSCTL_COMMAND % "eth0"]

        # Connect the container to its networks (starting from the second, the first is already connected above)
        for (iface_num, machine_link) in islice(machine.interfaces.items(), 1, None):
            machine_link.api_object.connect(machine_container)

            # Add the rp_filter patch for this interface
            rp_filter_commands.append(SYSCTL_COMMAND % ("eth%d" % iface_num))

        if not bridged_connected and machine.bridge:
            machine.bridge.api_object.connect(machine_container)

        machine.api_object = machine_container

    def update(self, machine):
        container_name = self.get_container_name(machine.name, machine.lab.folder_hash)
        machines = self.get_machines_by_filters(container_name=container_name)

        if not machines:
            raise Exception("Machine `%s` not found." % machine.name)

        machine.api_object = machines.pop()

        attached_networks = machine.api_object.attrs["NetworkSettings"]["Networks"]
        last_interface = len(attached_networks) - 1 if "none" in attached_networks else len(attached_networks)

        rp_filter_commands = []
        # Connect the container to its new networks
        for (_, machine_link) in machine.interfaces.items():
            machine_link.api_object.connect(machine.api_object)

            # Add the rp_filter patch for this interface
            rp_filter_commands.append(SYSCTL_COMMAND % ("eth%d" % last_interface))

            last_interface += 1

        # Execute the rp_filter patch for the new interfaces
        machine.api_object.exec_run(cmd=[Setting.get_instance().machine_shell, '-c', "; ".join(rp_filter_commands)],
                                    stdout=False,
                                    stderr=False,
                                    privileged=True,
                                    detach=True
                                    )

    @staticmethod
    def start(machine):
        # Build sysctl rp_filter commands for interfaces
        rp_filter_commands = []

        # Build the rp_filter patch for the interfaces
        for (iface_num, machine_link) in machine.interfaces.items():
            rp_filter_commands.append(SYSCTL_COMMAND % ("eth%d" % iface_num))

        try:
            machine.api_object.start()
        except APIError as e:
            if e.response.status_code == 500 and e.explanation.startswith('Mounts denied'):
                raise MountDeniedError("Host drive is not shared with Docker.")
            else:
                raise e

        # Build the final startup commands string
        startup_commands_string = "; ".join(STARTUP_COMMANDS)\
                                      .format(machine_name=machine.name,
                                              rp_filter="; ".join(rp_filter_commands),
                                              machine_commands="; ".join(machine.startup_commands)
                                              )

        # Execute the startup commands inside the container
        machine.api_object.exec_run(cmd=[Setting.get_instance().machine_shell, '-c', startup_commands_string],
                                    stdout=False,
                                    stderr=False,
                                    privileged=True,
                                    detach=True
                                    )

        if Setting.get_instance().open_terminals:
            machine.connect(Setting.get_instance().terminal)

    def undeploy(self, lab_hash, selected_machines=None):
        machines = self.get_machines_by_filters(lab_hash=lab_hash)

        for machine in machines:
            # If selected machines list is empty, remove everything
            # Else, check if the machine is in the list.
            if not selected_machines or \
               machine.labels["name"] in selected_machines:
                self.delete_machine(machine)

    def wipe(self, user=None):
        machines = self.get_machines_by_filters(user=user)

        for machine in machines:
            self.delete_machine(machine)

    def connect(self, lab_hash, machine_name, shell):
        container_name = self.get_container_name(machine_name, lab_hash)

        logging.debug("Connect to machine with container name: %s" % container_name)

        containers = self.get_machines_by_filters(lab_hash=lab_hash, container_name=container_name)

        logging.debug("Found containers: %s" % str(containers))

        if len(containers) != 1:
            raise Exception("Error getting the machine `%s` inside the lab." % machine_name)
        else:
            container = containers[0]
            if container.name != container_name:
                raise Exception("Error getting the machine `%s` inside the lab. "
                                "Did you mean %s?" % (machine_name, container.labels["name"]))

        if not shell:
            shell = Setting.get_instance().machine_shell

        def tty_connect():
            # Import PseudoTerminal only on Linux since some libraries are not available on Windows
            from ...trdparty.dockerpty.pty import PseudoTerminal

            # Needed with low level api because we need the id of the exec_create
            resp = self.client.api.exec_create(container.id,
                                               shell,
                                               stdout=True,
                                               stderr=True,
                                               stdin=True,
                                               tty=True,
                                               privileged=True
                                               )

            exec_output = self.client.api.exec_start(resp['Id'],
                                                     tty=True,
                                                     socket=True,
                                                     demux=True
                                                     )

            PseudoTerminal(self.client, exec_output, resp['Id']).start()

        def cmd_connect():
            Popen(["docker", "exec", "-it", "--privileged", container.id, shell])

        utils.exec_by_platform(tty_connect, cmd_connect, tty_connect)

    def get_machines_by_filters(self, lab_hash=None, container_name=None, user=None):
        filters = {"label": "app=kathara"}
        if user:
            filters["label"] = "user=%s" % user
        if lab_hash:
            filters["label"] = "lab_hash=%s" % lab_hash
        if container_name:
            filters["name"] = container_name

        return self.client.containers.list(all=True, filters=filters)

    @staticmethod
    def get_container_name(name, lab_hash):
        lab_hash = lab_hash if lab_hash else ""
        return "%s_%s_%s_%s" % (Setting.get_instance().machine_prefix, utils.get_current_user_name(), name, lab_hash)

    @staticmethod
    def delete_machine(machine):
        # Build the shutdown command string
        shutdown_commands_string = "; ".join(SHUTDOWN_COMMANDS).format(machine_name=machine.labels["name"])

        # Execute the shutdown commands inside the container (only if it's running)
        if machine.status == "running":
            machine.exec_run(cmd=[Setting.get_instance().machine_shell, '-c', shutdown_commands_string],
                             stdout=False,
                             stderr=False,
                             privileged=True,
                             detach=True
                             )

        machine.remove(force=True)
