import logging
import os
from typing import Optional


class Networking(object):
    """
    Class responsible for managing ExternalLink objects attaching Kathara collision domain to host interfaces.
    """

    @staticmethod
    def get_or_new_interface(full_interface_name: str, vlan_interface_name: str, vlan_id: Optional[int] = None) -> int:
        """
        Get or create an interface on the host. Return the link index.

        Args:
            full_interface_name (str): The name of the network interface of the host.
            vlan_interface_name (str): The name of the corresponding VLAN interface (MAX 15 chars).
            vlan_id (Optional[int]): The VLAN ID. If specified get or create a VLAN interface.

        Returns:
            int: The link index.
        """
        # disable pyroute2 logging to avoid warning about project structure changes
        logging.getLogger('pyroute2').disabled = True
        from pyroute2 import IPRoute
        ip = IPRoute()
        logging.getLogger('pyroute2').disabled = False

        logging.debug("Searching for interface `%s`..." % full_interface_name)

        # Search the interface
        interface_indexes = ip.link_lookup(ifname=full_interface_name)
        # If not present, raise an error
        if not interface_indexes:
            raise Exception("Interface `%s` not found." % full_interface_name)

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
    def attach_interface_to_bridge(interface_index: int, bridge_name: str) -> None:
        """
        Attach an interface to the bridge.

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
    def remove_interface(interface_name: str) -> None:
        """
        Remove an interface from the host.

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
        """
        Return the iptables version.

        Returns:
            str: The iptables version.
        """
        return os.popen("/sbin/iptables --version").read().strip()
