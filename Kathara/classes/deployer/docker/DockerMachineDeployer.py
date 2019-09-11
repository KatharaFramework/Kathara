import os

import docker

from classes.setting.Setting import Setting

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

    def __init__(self):
        self.client = docker.from_env()

    def deploy(self, machine):
        # Container image, if defined in machine meta. If not use default one.
        image = machine.meta["image"] if "image" in machine.meta else Setting.get_instance().image
        # Memory limit, if defined in machine meta.
        memory = machine.meta["mem"].upper() if "mem" in machine.meta else None
        # Bind the port 3000 of the container to a defined port (if present).
        ports = None
        if "port" in machine.meta:
            try:
                ports = {'3000/tcp': int(machine.meta["port"])}
            except ValueError:
                pass

        # Get the first network object, if defined.
        # This should be used in container create function
        first_network = machine.interfaces[0].network_object if 0 in machine.interfaces else None

        # Sysctl params to pass to the container creation
        sysctl_parameters = {RP_FILTER_NAMESPACE % x: 0 for x in ["all", "default", "lo"]}

        volumes = {machine.lab.shared_folder: {'bind': '/shared', 'mode': 'rw'}}

        machine_container = self.client.containers.create(image=image,
                                                          name=self._get_container_name(machine.name),
                                                          hostname=machine.name,
                                                          privileged=True,
                                                          network=first_network.name,
                                                          sysctls=sysctl_parameters,
                                                          mem_limit=memory,
                                                          ports=ports,
                                                          tty=True,
                                                          stdin_open=True,
                                                          detach=True,
                                                          volumes=volumes,
                                                          labels={"lab_hash": machine.lab.folder_hash,
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

        from socket import SocketIO

        # Execute the startup commands inside the container
        machine_container.exec_run(cmd=['bash', '-c', startup_commands_string],
                                   stdout=False,
                                   stderr=False,
                                   privileged=True,
                                   detach=True
                                   )

        return machine_container

    def undeploy(self, lab_hash):
        containers = self.client.containers.list(all=True, filters={"label": "lab_hash=%s" % lab_hash})

        for container in containers:
            container.remove(force=True)

    def wipe(self):
        containers = self.client.containers.list(all=True, filters={"label": "app=kathara"})

        for container in containers:
            container.remove(force=True)

    # noinspection PyMethodMayBeStatic
    def _get_container_name(self, name):
        return "%s_%s_%s" % (Setting.get_instance().machine_prefix, os.getlogin(), name)
