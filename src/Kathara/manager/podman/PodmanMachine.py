import logging
import re
import shlex
import sys
import tarfile
import tempfile
import time
from itertools import islice
from multiprocessing.dummy import Pool
from typing import List, Dict, Generator, Optional, Set, Tuple, Union, Any

import chardet
import podman.domain.containers
import podman.domain.networks
from podman import PodmanClient
from podman.errors import APIError

from .interfaces import IFACE_ALIAS_PREFIX, build_iface_alias, parse_iface_alias  # noqa: F401
from .libpod_compat import LibpodCompat
from .PodmanImage import PodmanImage
from .exec_stream.PodmanExecStream import PodmanExecStream
from .rootless import not_supported_in_rootless
from .stats.PodmanMachineStats import PodmanMachineStats
from ... import utils
from ...decorators import privileged
from ...event.EventDispatcher import EventDispatcher
from ...exceptions import MachineAlreadyExistsError, MachineBinaryError, MachineNotRunningError, \
    InvocationError, MachineOptionError, MountDeniedError
from ...model.Interface import Interface
from ...model.Lab import Lab
from ...model.Link import Link, BRIDGE_LINK_NAME
from ...model.Machine import Machine, MACHINE_CAPABILITIES
from ...setting.Setting import Setting

RP_FILTER_NAMESPACE = "net.ipv4.conf.%s.rp_filter"
OCI_RUNTIME_RE = re.compile(
    r"OCI runtime exec failed(.*?)(stat (.*): no such file or directory|exec: \"(.*)\": executable file not found)"
)

# libpod reports a generic "oci" runtime name per-container, never "crun": the error message
# itself is what tells us it's a missing-binary failure, not the runtime field.

# Per-interface sysctls (`net.ipv{4,6}.{conf,neigh}.ethN.*`): group 2 is the interface name.
IFACE_SYSCTL_RE = re.compile(r"net\.ipv[46]\.(conf|neigh)\.(eth\d+)\.")

def get_container_ifaces(container: podman.domain.containers.Container,
                         networks_by_name: Dict[str, podman.domain.networks.Network]) -> Dict[str, Dict[str, Any]]:
    """Rebuild the per-link interface metadata of a container from its network attachments.

    Native libpod network-attachment data has no equivalent of Docker's endpoint `DriverOpts`: the
    interface number is read back from the `kathara-eth<N>` alias of each attachment (see
    `build_iface_alias`), and the MAC address from the attachment's `MacAddress`.

    Args:
        container (podman.domain.containers.Container): A Podman container, already reloaded.
        networks_by_name (Dict[str, podman.domain.networks.Network]): Kathará Podman networks
            (labeled `app=kathara`), keyed by Podman network name, used to resolve each attachment
            to its Kathará link name through the network's `name` label.

    Returns:
        Dict[str, Dict[str, Any]]: The Kathará link name as key, and a dict with `num`, `mac_address`
        and the resolved `network` (podman.domain.networks.Network) as value, for every attachment
        that has a `kathara-eth<N>` alias and matches a Kathará network in `networks_by_name`.
    """
    attached_networks = container.attrs.get("NetworkSettings", {}).get("Networks", {}) or {}

    ifaces = {}
    for network_name, net_settings in attached_networks.items():
        network = networks_by_name.get(network_name)
        if network is None:
            continue

        link_name = network.attrs.get("labels", {}).get("name")
        if not link_name:
            continue

        iface_num = None
        for alias in net_settings.get("Aliases") or []:
            iface_num = parse_iface_alias(alias)
            if iface_num is not None:
                break

        if iface_num is None:
            continue

        ifaces[link_name] = {
            "num": iface_num, "mac_address": net_settings.get("MacAddress") or None, "network": network
        }

    return ifaces


# Kathará images declare `VOLUME /hosthome` and `VOLUME /shared`. Rootless Podman creates
# anonymous, uninitialized named volumes for any declared VOLUME that isn't otherwise mounted,
# and the container fails to start. A tmpfs mount on both paths keeps them harmless when the
# corresponding Kathará setting is disabled.
ANONYMOUS_VOLUME_PATHS = ["/hosthome", "/shared"]

# Known commands that each container should execute
# Run order: shared.startup, machine.startup and machine.meta['exec_commands']
STARTUP_COMMANDS = [
    # Unmount the /etc/resolv.conf and /etc/hosts files, automatically mounted by Podman inside the container.
    # In this way, they can be overwritten by custom user files.
    "umount /etc/resolv.conf",
    "umount /etc/hosts",

    # Copy the machine folder (if present) from the hostlab directory into the root folder of the container
    # In this way, files are all replaced in the container root folder
    "if [ -d \"/hostlab/{machine_name}\" ]; then "
    "(cd /hostlab/{machine_name} && tar c .) | (cd / && tar xhf - --no-same-owner --no-same-permissions); fi",

    # If /etc/hosts is not configured by the user, add the default mappings
    "if [ ! -s \"/etc/hosts\" ]; then "
    "echo '127.0.0.1 localhost' > /etc/hosts",
    "echo '::1 localhost' >> /etc/hosts",
    "echo '127.0.1.1 {machine_name}' >> /etc/hosts",
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

# Standard cgroup CPU period (microseconds) used to translate Kathará's `cpus` fraction into
# cpu_period/cpu_quota: podman-py silently drops `nano_cpus` (see containers_create.py), unlike
# docker-py, so it cannot be reused here.
CPU_PERIOD = 100000


class PodmanMachine(object):
    """The class responsible for deploying Kathara devices as Podman containers and interact with them."""
    __slots__ = ['client', 'podman_image', 'libpodCompat']

    def __init__(self, client: PodmanClient, podman_image: PodmanImage) -> None:
        self.client: PodmanClient = client
        self.podman_image: PodmanImage = podman_image
        self.libpodCompat: LibpodCompat = LibpodCompat(self.client)

    def deploy_machines(self, lab: Lab, selected_machines: Set[str] = None, excluded_machines: Set[str] = None) -> None:
        """Deploy all the network scenario devices as Podman containers.

        Args:
            lab (Kathara.model.Lab.Lab): A Kathara network scenario.
            selected_machines (Set[str]): A set containing the name of the devices to deploy.
            excluded_machines (Set[str]): A set containing the name of the devices to exclude.

        Returns:
            None

        Raises:
            NotSupportedError: If the privileged mode is active on any of the devices to deploy.
            InvocationError: If both `selected_machines` and `excluded_machines` are specified.
        """
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
        self.podman_image.check_from_list(lab_images)

        policy = Setting.get_instance().volume_mount_policy
        lab.add_option("_mount_volumes", policy in ['Prompt', 'Always'])
        machines_with_volumes = dict(filter(lambda x: len(x[1].meta['volumes']) > 0, machines))
        if len(machines_with_volumes) > 0:
            EventDispatcher.get_instance().dispatch(
                "machines_with_volumes", lab=lab, machines_with_volumes=machines_with_volumes
            )

        shared_mount = lab.general_options['shared_mount'] if 'shared_mount' in lab.general_options \
            else Setting.get_instance().shared_mount
        if shared_mount:
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

        # Delete to avoid keeping dirty state
        del lab.general_options['_mount_volumes']

    def _deploy_and_start_machine(self, machine_item: Tuple[str, Machine]) -> None:
        """Deploy and start a Podman container from the device contained in machine_item.

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
        """Create a Podman container representing the device and assign it to machine.api_object.

        Args:
            machine (Kathara.model.Machine.Machine): A Kathara device.

        Returns:
            None

        Raises:
            MachineAlreadyExistsError: If a device with the name specified already exists.
            NotSupportedError: If the device requires privileged mode.
            APIError: If the Podman APIs return an error.
        """
        logging.debug("Creating device `%s`..." % machine.name)

        containers = self.get_machines_api_objects_by_filters(machine_name=machine.name, lab_hash=machine.lab.hash,
                                                               user=utils.get_current_user_name())
        if containers:
            raise MachineAlreadyExistsError(machine.name)

        image = machine.get_image()
        memory = machine.get_mem()
        cpu_quota = machine.get_cpu(multiplier=CPU_PERIOD)
        ulimits = [{"Name": k, "Soft": v["soft"], "Hard": v["hard"]} for k, v in machine.get_ulimits().items()]

        # podman-py's create() unpacks these directly with a non-None default (e.g. `args.pop("ports", {})`):
        # passing `None` explicitly for them (instead of omitting the kwarg) crashes inside `_render_payload`,
        # so they're always built as empty collections rather than left as `None`.
        ports = {}
        for (host_port, protocol), guest_port in machine.get_ports().items():
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
        # Podman containers must be created already attached to their first network: unlike Docker,
        # `network_mode="none"` followed by a `connect()` does not work reliably.
        first_network = None
        first_machine_iface = None
        if machine.interfaces:
            first_machine_iface = machine.interfaces[0]
            first_network = first_machine_iface.link.api_object

        if machine.is_bridged():
            machine.add_meta("bridged_iface", max(machine.interfaces.keys()) + 1 if machine.interfaces else 0)

        # If no interfaces are declared in machine, but bridged mode is required, get bridge as first link.
        # Flag that bridged is already connected (because there's another check in `start`).
        if first_machine_iface is None and machine.is_bridged():
            first_network = machine.lab.get_or_new_link(BRIDGE_LINK_NAME).api_object
            machine.add_meta("_bridge_connected", True)

        # Sysctl params to pass to the container creation.
        # Only device-wide sysctls go here: per-interface sysctls (`net.ipv{4,6}.{conf,neigh}.ethN.*`) are applied
        # by the Kathará network plugin when each interface is attached, both at create time and at runtime
        # (see `_get_iface_sysctls`), like Docker Engine >= 27 does with `com.docker.network.endpoint.sysctls`.
        sysctl_parameters = {RP_FILTER_NAMESPACE % x: 0 for x in ["all", "default", "lo"]}
        sysctl_parameters["net.ipv4.ip_forward"] = 1
        sysctl_parameters["net.ipv4.icmp_ratelimit"] = 0

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

        # Merge machine sysctls (user-provided values take precedence), then keep only the device-wide ones.
        # Podman wants string values.
        sysctl_parameters = {**sysctl_parameters, **machine.get_sysctls()}
        sysctl_parameters = {k: str(v) for k, v in sysctl_parameters.items() if not IFACE_SYSCTL_RE.match(k)}

        volumes = {}
        mounts = []
        disable_selinux_label = False
        
        lab_options = machine.lab.general_options
        shared_mount = lab_options['shared_mount'] if 'shared_mount' in lab_options else \
            Setting.get_instance().shared_mount
        if shared_mount and machine.lab.shared_path:
            #volumes[machine.lab.shared_path] = {'bind': '/shared', 'mode': 'rw'}
            # /shared is a Kathará-owned lab folder: relabeling it for containers (SELinux `z`) is safe,
            # and keeps the device confined
            volumes[machine.lab.shared_path] = {'bind': '/shared', 'mode': 'rw', 'extended_mode': ['z']}
        # Mount the host home only if specified in settings.
        hosthome_mount = lab_options['hosthome_mount'] if 'hosthome_mount' in lab_options else \
            Setting.get_instance().hosthome_mount
        if hosthome_mount:
            volumes[utils.get_current_user_home()] = {'bind': '/hosthome', 'mode': 'rw'}
            disable_selinux_label = True

        try:
            for host_path, volume in machine.get_volumes().items():
                missing_permissions = utils.check_directory_permissions(host_path, volume['mode'])

                if not missing_permissions:
                    volumes[host_path] = {'bind': volume['guest_path'], 'mode': volume['mode']}
                    disable_selinux_label = True
                else:
                    raise PermissionError(
                        f"To mount volume `{host_path}` in `{volume['guest_path']}` "
                        f"you miss the following permissions: `{', '.join(missing_permissions)}`."
                    )
        except MountDeniedError:
            logging.warning(f"Volumes of device `{machine.name}` will not be mounted.")

        # Anonymous-volume fix: guarantee a mount on every declared VOLUME path not already covered,
        # otherwise rootless Podman creates an uninitialized anonymous volume and start fails.
        bound_guest_paths = {v['bind'] for v in volumes.values()}
        for guest_path in ANONYMOUS_VOLUME_PATHS:
            if guest_path not in bound_guest_paths:
                mounts.append({"type": "tmpfs", "source": "tmpfs", "target": guest_path})

        privileged_flag = machine.is_privileged()
        if privileged_flag:
            not_supported_in_rootless("Privileged devices")

        networks = None
        if first_machine_iface:
            networks = {first_network.name: self._get_network_options(machine, first_machine_iface)}
        elif first_network:
            # Bridged-only device: the bridge is a plain Podman network, not a Kathará plugin network,
            # so it only gets the interface name Kathará expects (no MAC, no plugin sysctls).
            networks = {first_network.name: {
                "interface_name": f"eth{machine.meta['bridged_iface']}",
                "aliases": [build_iface_alias(machine.meta['bridged_iface'])]
            }}

        container_name = self.get_container_name(machine.name, machine.lab.hash)

        try:
            labels = {"name": machine.name,
                      "lab_hash": machine.lab.hash,
                      "user": utils.get_current_user_name(),
                      "app": "kathara",
                      "shell": machine.meta["shell"]
                      if "shell" in machine.meta
                      else Setting.get_instance().device_shell
                      }
            if machine.is_bridged():
                labels["bridged_iface"] = str(machine.meta["bridged_iface"])

            entrypoint = shlex.split(machine.meta["entrypoint"]) if "entrypoint" in machine.meta else None
            args = machine.meta["args"] if "args" in machine.meta and machine.meta["args"] else None
            if args:
                args = shlex.split(args) if type(args) == str else args

            create_kwargs = dict(
                image=image,
                name=container_name,
                hostname=machine.name,
                cap_add=MACHINE_CAPABILITIES if not privileged_flag else None,
                privileged=privileged_flag,
                environment=machine.meta['envs'],
                sysctls=sysctl_parameters,
                mem_limit=memory,
                cpu_period=CPU_PERIOD if cpu_quota is not None else None,
                cpu_quota=cpu_quota,
                ports=ports,
                tty=True,
                stdin_open=True,
                detach=True,
                volumes=volumes,
                mounts=mounts,
                labels=labels,
                ulimits=ulimits,
                entrypoint=entrypoint,
                command=args
            )
            # libpod requires an explicit `bridge` netns mode when `networks` carry per-network options
            # such as a static MAC address: otherwise it rejects the spec ("networks and static ip/mac address
            # can only be used with Bridge mode networking").
            if networks:
                create_kwargs["networks"] = networks
                create_kwargs["network_mode"] = "bridge"
            else:
                create_kwargs["network_mode"] = "none"
            
            # Only disable SELinux label separation when a mount cannot be relabeled (the user home for
            # `/hosthome`, or an arbitrary user volume): `/shared` is a Kathará-owned folder and keeps its
            # normal confinement via the `z` relabel on its own mount above.
            if disable_selinux_label:
                create_kwargs["security_opt"] = ["disable"]

            machine_container = self.client.containers.create(**create_kwargs)
        except APIError as e:
            raise e

        # Pack machine files into a tar.gz and extract its content inside `/`
        tar_data = machine.pack_data()
        if tar_data:
            self.copy_files(machine_container, "/", tar_data)

        machine.api_object = machine_container

    def connect_interface(self, machine: Machine, interface: Interface) -> None:
        """Connect the Podman container representing the machine to a specified collision domain.

        Args:
            machine (Kathara.model.Machine.Machine): A Kathara device.
            interface (Kathara.model.Interface.Interface): A Kathara interface object.

        Returns:
            None

        Raises:
            APIError: If the Podman APIs return an error, including when the network plugin fails
                to apply an interface sysctl.
        """
        machine.api_object.reload()
        attached_networks = machine.api_object.attrs.get("NetworkSettings", {}).get("Networks", {})

        if interface.link.api_object.name not in attached_networks:
            self.libpodCompat.network_connect(
                interface.link.api_object, machine.api_object, f"eth{interface.num}",
                mac_address=interface.mac_address,
                sysctls=self._get_iface_sysctls(machine, interface.num),
                aliases=[build_iface_alias(interface.num)],
            )

    @staticmethod
    def _get_iface_sysctls(machine: Machine, interface_num: int) -> Dict[str, Any]:
        """Return the sysctls of a single interface of the device.

        Mirrors the per-endpoint sysctls of the Docker backend (Docker Engine >= 27): Kathará defaults for every
        interface, overridden by the user sysctls that target this interface.

        Args:
            machine (Kathara.model.Machine.Machine): A Kathara device.
            interface_num (int): The number of the interface.

        Returns:
            Dict[str, Any]: The sysctls to apply to the interface, with the explicit interface name (e.g. `eth1`).
        """
        iface = f"eth{interface_num}"
        sysctls = {RP_FILTER_NAMESPACE % iface: 0}
        if machine.is_ipv6_enabled():
            sysctls[f"net.ipv6.conf.{iface}.disable_ipv6"] = 0
            sysctls[f"net.ipv6.conf.{iface}.forwarding"] = 1
        else:
            sysctls[f"net.ipv6.conf.{iface}.disable_ipv6"] = 1

        for key, value in machine.get_sysctls().items():
            match = IFACE_SYSCTL_RE.match(key)
            if match and match.group(2) == iface:
                sysctls[key] = value

        return sysctls

    def _get_network_options(self, machine: Machine, interface: Interface) -> Dict[str, Any]:
        """Return the per-network options used to attach an interface at container creation.

        Args:
            machine (Kathara.model.Machine.Machine): A Kathara device.
            interface (Kathara.model.Interface.Interface): The interface attached at creation.

        Returns:
            Dict[str, Any]: The libpod per-network options (interface name, alias, static MAC, plugin options).
        """
        options = {"interface_name": f"eth{interface.num}", "aliases": [build_iface_alias(interface.num)]}
        if interface.mac_address:
            options["static_mac"] = interface.mac_address
        plugin_options = LibpodCompat.sysctl_options(self._get_iface_sysctls(machine, interface.num))
        if plugin_options:
            options["options"] = plugin_options
        return options

    @staticmethod
    def disconnect_from_link(machine: Machine, link: Link) -> None:
        """Disconnect the Podman container representing the machine from a specified collision domain.

        Args:
            machine (Kathara.model.Machine): A Kathara device.
            link (Kathara.model.Link): A Kathara collision domain object.

        Returns:
            None
        """
        machine.api_object.reload()
        attached_networks = machine.api_object.attrs.get("NetworkSettings", {}).get("Networks", {})

        if link.api_object.name in attached_networks:
            link.api_object.disconnect(machine.api_object)

    def start(self, machine: Machine) -> None:
        """Start the Podman container representing the device.

        Connect the container to the networks, run the startup commands and open a terminal (if requested).

        Args:
           machine (Kathara.model.Machine.Machine): A Kathara device.

        Returns:
            None

        Raises:
            APIError: If the Podman APIs return an error.
        """
        logging.debug("Starting device `%s`..." % machine.name)

        try:
            machine.api_object.start()
        except APIError as e:
            # Never started, so netavark never ran the plugin for it: removing the container
            # leaves no network state behind.
            try:
                machine.api_object.remove(force=True)
            except APIError as remove_error:
                logging.debug(f"Cannot remove device `{machine.name}` after a failed start: {remove_error}")
            raise self._translate_start_error(machine, e) from e

        # Connect the container to its networks (starting from the second, the first is already connected in `create`)
        for (iface_num, machine_iface) in islice(machine.interfaces.items(), 1, None):
            logging.debug(
                f"Connecting device `{machine.name}` to collision domain `{machine_iface.link.name}` "
                f"on interface {iface_num}..."
            )
            self.connect_interface(machine, machine_iface)

        # Bridged connection required but not added in `deploy` method.
        if "_bridge_connected" not in machine.meta and machine.is_bridged():
            bridge_link = machine.lab.get_or_new_link(BRIDGE_LINK_NAME).api_object
            # Plain Podman network: only the interface name and alias, no MAC or plugin sysctls.
            # The interface number is also kept in the `bridged_iface` label.
            self.libpodCompat.network_connect(bridge_link, machine.api_object, f"eth{machine.meta['bridged_iface']}",
                                              aliases=[build_iface_alias(machine.meta['bridged_iface'])])

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

        # Delete to avoid keeping dirty state
        if '_bridge_connected' in machine.meta:
            del machine.meta['_bridge_connected']

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
        if selected_machines is not None and excluded_machines is not None:
            raise InvocationError(f"You can either specify `selected_machines` or `excluded_machines`.")

        containers = self.get_machines_api_objects_by_filters(lab_hash=lab_hash, user=utils.get_current_user_name())
        if selected_machines is not None:
            containers = [item for item in containers if item.labels["name"] in selected_machines]
        elif excluded_machines is not None:
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

    def _undeploy_machine(self, machine_api_object: podman.domain.containers.Container) -> None:
        """Undeploy a Podman container.

        Args:
            machine_api_object (podman.domain.containers.Container): The Podman container to undeploy.

        Returns:
            None
        """
        self._delete_machine(machine_api_object)

        EventDispatcher.get_instance().dispatch("machine_undeployed", item=machine_api_object)

    def connect(self, lab_hash: str, machine_name: str, user: str = None, shell: str = None,
                logs: bool = False, wait: Union[bool, Tuple[int, float]] = True) -> None:
        """Open a stream to the Podman container specified by machine_name using the specified shell.

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
            NotSupportedError: If invoked on Windows (Podman remote/SSH exec hijack is not supported yet).
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

        startup_waited = 0
        if should_wait:
            startup_waited = self._wait_startup_execution(container, n_retries=n_retries, retry_interval=retry_interval)

            EventDispatcher.get_instance().dispatch("machine_startup_wait_ended")

            if startup_waited == 2:
                return

        if logs and Setting.get_instance().print_startup_log:
            # Get the logs, if the command fails it means that the shell is not found.
            cat_logs_cmd = "cat /var/log/shared.log /var/log/startup.log /var/kathara/*"
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

        exec_id = self.libpodCompat.exec_create(container.id, shell, stdout=True, stderr=True,
                                                stdin=True, tty=True, privileged=False)
        hijacked_socket = self.libpodCompat.exec_start_hijack(exec_id, tty=True)

        def tty_connect():
            from .terminal.PodmanTTYTerminal import PodmanTTYTerminal
            try:
                PodmanTTYTerminal(hijacked_socket, self.client, exec_id).start()
            except Exception:
                hijacked_socket.close()
                raise

        def not_supported():
            from ...exceptions import NotSupportedError
            hijacked_socket.close()
            raise NotSupportedError("Podman backend does not support connecting to a device from Windows yet.")

        utils.exec_by_platform(tty_connect, not_supported, tty_connect)

    def exec(self, lab_hash: str, machine_name: str, command: Union[str, List], user: str = None,
             tty: bool = True, wait: Union[bool, Tuple[int, float]] = False, stream: bool = True) \
            -> Union[PodmanExecStream, Tuple[bytes, bytes, int]]:
        """Execute the command on the Podman container specified by the lab_hash and the machine_name.

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
            stream (bool): If True, return a PodmanExecStream object.
                If False, returns a tuple containing the complete stdout, the stderr, and the return code of the command.

        Returns:
             Union[PodmanExecStream, Tuple[bytes, bytes, int]]: A PodmanExecStream object or
             a tuple containing the stdout, the stderr and the return code of the command.

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
            startup_waited = self._wait_startup_execution(container, n_retries=n_retries, retry_interval=retry_interval)

            if startup_waited == 2:
                raise MachineNotRunningError(machine_name)

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
            return PodmanExecStream(exec_result['output'], exec_result['Id'], self.client)

        return exec_result['output'][0], exec_result['output'][1], exec_result['exit_code']

    def _exec_run(self, container: podman.domain.containers.Container,
                  cmd: Union[str, List], stdout=True, stderr=True, stdin=False, tty=False,
                  privileged=False, user='', detach=False, stream=False,
                  environment=None, workdir=None, demux=False) -> Dict[str, Optional[Any]]:
        """Custom implementation of an exec run that also checks if the executed binary exists.

        Args:
            container (podman.domain.containers.Container): Container object on which the command is executed.
            cmd (str or list): Command to be executed
            stdout (bool): Attach to stdout. Default: ``True``
            stderr (bool): Attach to stderr. Default: ``True``
            stdin (bool): Attach to stdin. Default: ``False``
            tty (bool): Allocate a pseudo-TTY. Default: False
            privileged (bool): Run as privileged.
            user (str): User to execute command as. Default: root
            detach (bool): If true, detach from the exec command. Default: False
            stream (bool): Stream response data. Default: False
            environment (dict or list): A dictionary or a list of strings in the following format
                ``["PASSWORD=xxx"]`` or ``{"PASSWORD": "xxx"}``.
            workdir (str): Path to working directory for this exec session
            demux (bool): Return stdout and stderr separately

        Returns:
            (Dict): A dict of (exit_code, Id, output)
                exit_code: (int):
                    Exit code for the executed command or ``None`` if ``stream`` is ``True``.
                Id: (str):
                    The exec id from Podman.
                output: (generator, bytes, or tuple):
                    If ``stream=True``, a generator yielding response chunks.
                    If ``demux=True``, a tuple of two bytes: stdout and stderr.
                    A bytestring containing response data otherwise.

        Raises:
            APIError: If the server returns an error.
            MachineBinaryError: If the binary of the command is not found.
        """
        exec_id = self.libpodCompat.exec_create(
            container.id, cmd, stdout=stdout, stderr=stderr, stdin=stdin, tty=tty,
            privileged=privileged, user=user, environment=environment, workdir=workdir,
        )

        try:
            exec_output = self.libpodCompat.exec_start(exec_id, tty=tty, detach=detach,
                                                       stream=stream, demux=demux)
        except APIError as e:
            matches = OCI_RUNTIME_RE.search(e.explanation or str(e))
            if matches:
                raise MachineBinaryError(matches.group(3) or matches.group(4), container.labels['name'])

            raise e

        exit_code = self.libpodCompat.exec_inspect(exec_id).get('ExitCode')
        if not stream and (exit_code is not None and exit_code != 0):
            (stdout_out, _) = exec_output if demux else (exec_output, None)
            exec_stdout = ""
            if stdout_out:
                if type(stdout_out) is bytes:
                    char_encoding = chardet.detect(stdout_out)
                    exec_stdout = stdout_out.decode(char_encoding['encoding']) if char_encoding['encoding'] else ""
                else:
                    exec_stdout = stdout_out
            matches = OCI_RUNTIME_RE.search(exec_stdout)
            if matches:
                raise MachineBinaryError(matches.group(3) or matches.group(4), container.labels['name'])

        if stream:
            return {'exit_code': None, 'Id': exec_id, 'output': exec_output}

        return {'exit_code': int(exit_code) if exit_code is not None else None, 'Id': exec_id, 'output': exec_output}

    def _wait_startup_execution(self, container: podman.domain.containers.Container,
                                n_retries: Optional[int] = None, retry_interval: float = 1) -> int:
        """Wait until the startup commands are executed or until the user requests the control over the device.

        Args:
            container (podman.domain.containers.Container): The Podman container to wait.
            n_retries (Optional[int]): Number of retries before stopping waiting. Default is None, waits indefinitely.
            retry_interval (float): The time interval in seconds to wait for each retry. Default is 1.

        Returns:
            int: 0 if the user requests the control before the ending of the startup. 1, if the startup ends.
                2 if an APIError occurred during execution.
        """
        logging.debug(f"Waiting startup commands execution for device {container.labels['name']}...")

        n_retries = n_retries if n_retries is None or n_retries >= 0 else abs(n_retries)
        retry_interval = retry_interval if retry_interval >= 0 else 1

        retries = 0
        is_cmd_success = False
        startup_waited = 1
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
                    startup_waited = int(False or is_cmd_success)
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
            except APIError:
                return 2

        return startup_waited

    @staticmethod
    def copy_files(machine_api_object: podman.domain.containers.Container, path: str, tar_data: bytes) -> None:
        """Copy the files contained in tar_data in the Podman container path specified by the machine_api_object.

        Args:
            machine_api_object (podman.domain.containers.Container): A Podman container.
            path (str): The path of the container where copy the tar_data.
            tar_data (bytes): The data to copy in the container.

        Returns:
            None
        """
        machine_api_object.put_archive(path, tar_data)

    @staticmethod
    def retrieve_files(machine_api_object: podman.domain.containers.Container, src: str, dst: str) -> None:
        """Get the file or directory from the Podman container specified by the machine_api_object into dst.

        Args:
            machine_api_object (podman.domain.containers.Container): A Podman container.
            src (str): The path of the file or folder to copy from the device.
            dst (str): The destination path on the host.

        Returns:
            None
        """
        # Get the tar from the container
        bits, stats = machine_api_object.get_archive(src)

        # Create a tmp tar file and write the chunks from the container
        with tempfile.NamedTemporaryFile(mode='wb+', suffix='.tar') as temp_file:
            for chunk in bits:
                temp_file.write(chunk)

            # After writing, go at the beginning of file
            temp_file.seek(0)

            # Now, we need to extract the tmp tar file into the destination folder
            with tarfile.open(fileobj=temp_file, mode='r') as tar_file:
                tar_file.extractall(path=dst)

    @privileged
    def get_machines_api_objects_by_filters(self, lab_hash: str = None, machine_name: str = None, user: str = None) -> \
            List[podman.domain.containers.Container]:
        """Return the Podman containers objects specified by lab_hash and user.

        Args:
            lab_hash (str): The hash of a network scenario. If specified, return all the devices in the scenario.
            machine_name (str): The name of a device. If specified, return the specified container of the scenario.
            user (str): The name of a user on the host. If specified, return only the containers of the user.

        Returns:
            List[podman.domain.containers.Container]: A list of Podman containers objects.
        """
        # podman-py's prepare_filters() stringifies list values of a filters *dict*
        # ({"label": ["a=b", "c=d"]} becomes {"label": ["['a=b', 'c=d']"]}): the list-of-strings form
        # ("key=value") is serialized correctly, so it is used instead. Revert once fixed upstream.
        filters = ["label=app=kathara"]
        if user:
            filters.append(f"label=user={user}")
        if lab_hash:
            filters.append(f"label=lab_hash={lab_hash}")
        if machine_name:
            filters.append(f"label=name={machine_name}")

        return self.client.containers.list(all=True, filters=filters, ignore_removed=True)

    def get_machines_stats(self, lab_hash: str = None, machine_name: str = None, user: str = None) -> \
            Generator[Dict[str, PodmanMachineStats], None, None]:
        """Return a generator containing the Podman devices' stats.

        Args:
            lab_hash (str): The hash of a network scenario. If specified, return all the stats of the devices in the
                scenario.
            machine_name (str): The name of a device. If specified, return the specified device stats.
            user (str): The name of a user on the host. If specified, return only the stats of the specified user.

        Returns:
            Generator[Dict[str, PodmanMachineStats], None, None]: A generator containing device names as keys and
            PodmanMachineStats as values.

        Raises:
            NotSupportedError: If user is None.
        """
        if user is None:
            not_supported_in_rootless("Statistics of all users")

        machines_stats = {}

        @privileged
        def load_machine_stats(machine):
            if machine.name not in machines_stats:
                machines_stats[machine.name] = PodmanMachineStats(machine)

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
        """Return the name of a Podman container.

        Args:
            name (str): The name of a Kathara device.
            lab_hash (str): The hash of a running scenario.

        Returns:
            str: The name of the Podman container in the format "|dev_prefix|_|username_prefix|_|name|_|lab_hash|".
        """
        lab_hash = lab_hash if "_%s" % lab_hash else ""
        return "%s_%s_%s_%s" % (Setting.get_instance().device_prefix, utils.get_current_user_name(), name, lab_hash)

    def _delete_machine(self, container: podman.domain.containers.Container) -> None:
        """Remove a running Podman container.

        Args:
            container (podman.domain.containers.Container): The Podman container to remove.

        Returns:
            None
        """
        # Build the shutdown command string
        shutdown_commands_string = "; ".join(SHUTDOWN_COMMANDS).format(machine_name=container.labels["name"])

        logging.debug(f"Executing shutdown commands on `{container.labels['name']}`: {shutdown_commands_string}")
        # Execute the shutdown commands inside the container (only if it's running)
        if LibpodCompat.container_status(container) == "running":
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
    
    @staticmethod 
    def _translate_start_error(machine: Machine, error: APIError) -> Exception:
        """Turn the libpod errors caused by rootless limits into readable Kathará errors."""
        explanation = error.explanation or str(error)

        # crun: "setrlimit `RLIMIT_NOFILE`: Operation not permitted"
        match = re.search(r"setrlimit `RLIMIT_(\w+)`", explanation)
        if match:
            name = match.group(1).lower()
            limit = machine.get_ulimits().get(name, {})
            return MachineOptionError(
                f"Cannot apply ulimit `{name}` (soft={limit.get('soft')}, hard={limit.get('hard')}) on device "
                f"`{machine.name}`: in rootless mode a limit cannot exceed the hard limit of the user running Podman "
                f"(check it with `ulimit -H`)."
            )

        # rootlessport: "rootlessport cannot expose privileged port 80, you can add ... (>= 1024): listen tcp ..."
        if "rootlessport cannot expose privileged port" in explanation:
            return MachineOptionError(f"Cannot publish a port of device `{machine.name}`: {explanation}")

        return error