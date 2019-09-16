import os
from subprocess import Popen

import utils
from ...setting.Setting import Setting

RP_FILTER_NAMESPACE = "net.ipv4.conf.%s.rp_filter"
SYSCTL_COMMAND = "sysctl %s=0" % RP_FILTER_NAMESPACE

# Known commands that each container should execute
# Run order: rp_filters, shared.startup, machine.startup and machine.startup_commands
STARTUP_COMMANDS = [
    # Copy the machine folder (if present) from the hostlab directory into the root folder of the container
    # In this way, files are all replaced in the container root folder
    "if [ -d \"/hostlab/{machine_name}\" ]; then "
    "chmod -R 777 /hostlab/{machine_name}/*; "
    "cp -rfp /hostlab/{machine_name}/* /; fi",

    # Create /var/log/zebra folder
    "mkdir /var/log/zebra",

    # Give proper permissions to few files/directories (copied from Kathara)
    "chmod -R 777 /var/log/quagga; chmod -R 777 /var/log/zebra; chmod -R 777 /var/www/*",

    # Placeholder for rp_filter patches
    "{rp_filter}",

    # If shared.startup file is present
    "if [ -f \"/hostlab/shared.startup\" ]; then "
    # Give execute permissions to the file and execute it
    # We redirect the output "&>" to a random file so we avoid blocking stdin/stdout 
    "chmod u+x /hostlab/shared.startup; /hostlab/shared.startup &> /tmp/startup_out; fi",

    # If .startup file is present
    "if [ -f \"/hostlab/{machine_name}.startup\" ]; then "
    # Give execute permissions to the file and execute it
    # We redirect the output "&>" to a random file so we avoid blocking stdin/stdout 
    "chmod u+x /hostlab/{machine_name}.startup; "
    "/hostlab/{machine_name}.startup &> /tmp/startup_out; fi",

    # Placeholder for user commands
    "{machine_commands}"
]


class DockerMachineDeployer(object):
    __slots__ = ['client']

    def __init__(self, client):
        self.client = client

    def deploy(self, machine, terminals, options, xterm):
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

        if "exec" in options:
            machine.add_meta("exec", options["exec"])

        # Get the first network object, if defined.
        # This should be used in container create function
        first_network = machine.interfaces[0].network_object if 0 in machine.interfaces else None

        # Sysctl params to pass to the container creation
        sysctl_parameters = {RP_FILTER_NAMESPACE % x: 0 for x in ["all", "default", "lo"]}

        volumes = {machine.lab.shared_folder: {'bind': '/shared', 'mode': 'rw'}}

        # Mount the host home only if specified in settings.
        if Setting.get_instance().hosthome_mount:
            volumes[os.path.expanduser('~')] = {'bind': '/hosthome', 'mode': 'rw'}

        machine_container = self.client.containers.create(image=image,
                                                          name=self.get_container_name(machine.name),
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
                                                                  "app": "kathara"
                                                                  }
                                                          )

        # Pack machine files into a tar.gz and extract its content inside `/`
        tar_data = machine.pack_data()
        if tar_data:
            machine_container.put_archive("/", tar_data)

        # Build sysctl rp_filter commands for interfaces (since eth0 is connected above, we already put it here)
        rp_filter_commands = [SYSCTL_COMMAND % "eth0"]

        # Connect the container to its networks (starting from the second, the first is already connected above)
        for (iface_num, machine_link) in machine.interfaces.items():
            if iface_num <= 0:
                continue

            machine_link.network_object.connect(machine_container)

            # Add the rp_filter patch for this interface
            rp_filter_commands.append(SYSCTL_COMMAND % ("eth%d" % iface_num))

        if machine.bridge:
            machine.bridge.network_object.connect(machine_container)

        machine_container.start()

        # Build the final startup commands string
        startup_commands_string = "; ".join(STARTUP_COMMANDS)\
                                      .format(machine_name=machine.name,
                                              rp_filter="; ".join(rp_filter_commands),
                                              machine_commands="; ".join(machine.startup_commands)
                                              )

        # Execute the startup commands inside the container
        machine_container.exec_run(cmd=[Setting.get_instance().machine_shell, '-c', startup_commands_string],
                                   stdout=False,
                                   stderr=False,
                                   privileged=True,
                                   detach=True
                                   )

        if terminals:
            machine.connect()

    def undeploy(self, lab_hash):
        containers = self.get_machines_by_filters(lab_hash=lab_hash)

        for container in containers:
            container.remove(force=True)

    def wipe(self):
        containers = self.get_machines_by_filters()

        for container in containers:
            container.remove(force=True)

    def connect(self, lab_hash, machine_name, command):
        container_name = self.get_container_name(machine_name)

        containers = self.get_machines_by_filters(lab_hash=lab_hash, container_name=container_name)

        if len(containers) != 1:
            raise Exception("Error getting the machine `%s` inside the lab." % machine_name)
        else:
            container = containers[0]

        if not command:
            command = Setting.get_instance().machine_shell

        def linux_connect():
            # Import PseudoTerminal only on Linux since some libraries are not available on Windows
            from ...trdparty.dockerpty.pty import PseudoTerminal

            # Needed with low level api because we need the id of the exec_create
            resp = self.client.api.exec_create(container.id,
                                               command,
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

        def windows_connect():
            Popen(["docker", "exec", "-it", "--privileged", container.id, command])

        utils.exec_by_platform(linux_connect, windows_connect, linux_connect)

    def get_machines_by_filters(self, lab_hash=None, container_name=None):
        filters = {"label": "app=kathara"}
        if lab_hash:
            filters["label"] = "lab_hash=%s" % lab_hash
        if container_name:
            filters["name"] = container_name

        return self.client.containers.list(all=True, filters=filters)

    @staticmethod
    def get_container_name(name):
        return "%s_%s_%s" % (Setting.get_instance().machine_prefix, os.getlogin(), name)
