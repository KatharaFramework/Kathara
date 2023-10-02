import logging
import os
import shutil
from typing import Optional

from ..exceptions import InterfaceNotFoundError


class Networking(object):
    """
    Class responsible for managing ExternalLink objects attaching Kathara collision domain to host interfaces.
    """

    @staticmethod
    def get_or_new_interface(full_interface_name: str, vlan_interface_name: str, vlan_id: Optional[int] = None) -> int:
        """Get or create an interface on the host. Return the OS link index.

        Args:
            full_interface_name (str): The name of the network interface of the host.
            vlan_interface_name (str): The name of the corresponding VLAN interface (MAX 15 chars).
            vlan_id (Optional[int]): The VLAN ID. If specified get or create a VLAN interface.

        Returns:
            int: The link index.

        Raises:
            InterfaceNotFoundError: If the specified interface is not found on the host machine.
        """
        from pyroute2 import IPRoute
        ip = IPRoute()

        logging.debug("Searching for interface `%s`..." % full_interface_name)

        # Search the interface
        interface_indexes = ip.link_lookup(ifname=full_interface_name)
        # If not present, raise an error
        if not interface_indexes:
            raise InterfaceNotFoundError(f"Interface `{full_interface_name}` not found on the host machine.")

        interface_index = interface_indexes[0]
        logging.debug("Interface found with ID = %d" % interface_index)

        if vlan_id:
            full_vlan_iface_name = "%s.%s" % (vlan_interface_name, vlan_id)
            logging.debug("VLAN Interface required... Creating `%s`..." % full_vlan_iface_name)

            # Search the VLAN interface
            vlan_link_indexes = ip.link_lookup(ifname=full_vlan_iface_name)

            if not vlan_link_indexes:
                # A VLAN interface should be created before attaching it to bridge.
                ip.link(
                    "add",
                    ifname=full_vlan_iface_name,
                    kind="vlan",
                    link=interface_index,
                    vlan_id=vlan_id
                )

                # Set the new interface up
                ip.link(
                    "set",
                    index=interface_index,
                    state="up"
                )

                logging.debug("Interface `%s` set UP." % full_vlan_iface_name)

                # Refresh the VLAN interface information
                vlan_link_indexes = ip.link_lookup(ifname=full_vlan_iface_name)
                interface_index = vlan_link_indexes[0]

        ip.close()

        return interface_index

    @staticmethod
    def attach_interface_ns(interface_name: str, interface_index: int, switch_path: str, ns_pid: int) -> None:
        """Attach an interface using namespaces.

        Args:
            interface_name (str): The full interface name of the interface to attach.
            interface_index (int): The interface index of the interface to attach.
            switch_path (str):  The path of the switch where to attach to the interface.
            ns_pid (int): The PID of the namespace.

        Returns:
            None
        """
        from pyroute2 import IPRoute
        from ..trdparty.nsenter.nsenter import nsenter

        logging.debug("Attaching interface ID = %d to namespace `%s`..." % (interface_index, switch_path))

        ip = IPRoute()
        ip.link(
            "set",
            index=interface_index,
            state="up"
        )
        ip.close()

        pid_path = os.path.join(switch_path, f"pid_{interface_name}")
        command = f"/bin/sh -c '/usr/local/bin/vde_ext -s {switch_path}/ctl -p {pid_path} {interface_name} &'"

        logging.debug("Running command `%s` in namespace `%s`..." % (command, switch_path))
        nsenter(ns_pid, command, ns_types=['ipc', 'net', 'pid', 'uts'])

        logging.debug("Interface ID = %d attached to namespace `%s`." % (interface_index, switch_path))

    @staticmethod
    def attach_interface_bridge(interface_index: int, bridge_name: str) -> None:
        """Attach an interface to a Linux bridge.

        Args:
            interface_index (int): The interface index of the interface to attach.
            bridge_name (str):  The name of the bridge to attach to the interface.

        Returns:
            None
        """
        from pyroute2 import IPRoute
        ip = IPRoute()

        logging.debug("Attaching interface ID = %d to bridge `%s`..." % (interface_index, bridge_name))
        bridge_index = ip.link_lookup(ifname=bridge_name)[0]

        ip.link(
            "set",
            index=interface_index,
            master=bridge_index,
            state="up"
        )

        logging.debug("Interface ID = %d attached to bridge %s." % (interface_index, bridge_name))

        ip.close()

    @staticmethod
    def remove_interface_ns(interface_name: str, switch_path: str, ns_pid: int) -> None:
        """Remove an interface using namespaces.

        Args:
            interface_name (str): The full interface name of the interface to remove.
            switch_path (str):  The path of the switch where to remove to the interface.
            ns_pid (int): The PID of the namespace.

        Returns:
            None
        """
        from ..trdparty.nsenter.nsenter import nsenter

        logging.debug("Killing vde_ext process in namespace `%s`." % switch_path)

        pid_path = os.path.join(switch_path, f"pid_{interface_name}")
        command = f"/bin/sh -c 'kill -2 $(cat {pid_path})'"

        logging.debug("Running command `%s` in namespace `%s`..." % (command, switch_path))
        nsenter(ns_pid, command, ns_types=['ipc', 'net', 'pid', 'uts'])

        logging.debug("vde_ext process killed in namespace `%s`." % switch_path)

    @staticmethod
    def remove_interface(interface_name: str) -> None:
        """Remove an interface from the host.

        Args:
            interface_name (str): The name of the interface to remove.

        Returns:
            None
        """
        from pyroute2 import IPRoute
        ip = IPRoute()

        logging.debug("Searching for interface `%s`..." % interface_name)

        # Search the interface
        link_indexes = ip.link_lookup(ifname=interface_name)
        # If not present, raise an error
        if not link_indexes:
            logging.debug("Interface `%s` not found, exiting..." % interface_name)
            return

        link_index = link_indexes[0]
        logging.debug("Interface found with ID = %d" % link_index)

        logging.debug("Removing interface with ID = %d" % link_index)
        ip.link(
            "del",
            index=link_index
        )
        ip.close()

    @staticmethod
    def get_iptables_version() -> str:
        """Return the iptables version on a Linux host.

        Returns:
            str: The iptables version.
        """
        iptables_binary = shutil.which("iptables")
        if iptables_binary is None:
            if os.path.exists("/sbin/iptables"):
                iptables_binary = "/sbin/iptables"
            elif os.path.exists("/usr/sbin/iptables"):
                iptables_binary = "/usr/sbin/iptables"

        if iptables_binary is None:
            raise FileNotFoundError("Cannot find `iptables` in the host.")

        logging.debug("Found iptables binary in `%s`." % iptables_binary)

        return os.popen("%s --version" % iptables_binary).read().strip()
