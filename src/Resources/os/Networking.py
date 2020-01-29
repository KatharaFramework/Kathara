import logging
import os


class Networking(object):
    @staticmethod
    def get_or_new_interface(interface_name, vlan=None):
        from pyroute2 import IPRoute
        ip = IPRoute()

        logging.debug("Searching for interface `%s`..." % interface_name)

        # Search the interface
        link_indexes = ip.link_lookup(ifname=interface_name)
        # If not present, raise an error
        if not link_indexes:
            raise Exception("Interface `%s` not found." % interface_name)

        link_index = link_indexes[0]
        logging.debug("Interface found with ID = %d" % link_index)

        if vlan:
            vlan_iface_name = "%s.%s" % (interface_name, vlan)
            logging.debug("VLAN Interface required... Creating `%s`..." % vlan_iface_name)

            # Search the VLAN interface
            vlan_link_indexes = ip.link_lookup(ifname=vlan_iface_name)

            if not vlan_link_indexes:
                # A VLAN interface should be created before attaching it to bridge.
                ip.link(
                    "add",
                    ifname=vlan_iface_name,
                    kind="vlan",
                    link=link_index,
                    vlan_id=vlan
                )

                # Set the new interface up
                ip.link(
                    "set",
                    index=link_index,
                    state="up"
                )

                logging.debug("Interface `%s` set UP." % vlan_iface_name)

                # Refresh the VLAN interface information
                vlan_link_indexes = ip.link_lookup(ifname=vlan_iface_name)
                link_index = vlan_link_indexes[0]

        ip.close()

        return link_index

    @staticmethod
    def attach_interface_to_bridge(interface_index, bridge_name):
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
    def remove_interface(interface_name):
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
    def get_iptables_version():
        return os.popen("/sbin/iptables --version").read().strip()
