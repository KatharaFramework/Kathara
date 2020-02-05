import logging
import os
import subprocess
import docker

class Networking(object):
    @staticmethod
    def get_or_new_interface(full_interface_name, vlan_interface_name, vlan_id=None):
        from pyroute2 import IPRoute
        ip = IPRoute()

        logging.debug("Searching for interface `%s`..." % full_interface_name)

        # Search the interface
        link_indexes = ip.link_lookup(ifname=full_interface_name)
        # If not present, raise an error
        if not link_indexes:
            raise Exception("Interface `%s` not found." % full_interface_name)

        link_index = link_indexes[0]
        logging.debug("Interface found with ID = %d" % link_index)

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
                    link=link_index,
                    vlan_id=vlan_id
                )

                # Set the new interface up
                ip.link(
                    "set",
                    index=link_index,
                    state="up"
                )

                logging.debug("Interface `%s` set UP." % full_vlan_iface_name)

                # Refresh the VLAN interface information
                vlan_link_indexes = ip.link_lookup(ifname=full_vlan_iface_name)
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

    @staticmethod
    def create_veth(name1,name2,i):
        if name1 == "":
            name1 = "host"+str(i)
        if name2 == "":
            name2 = "host"+str(i+10)
        from pyroute2 import IPRoute
        ip = IPRoute()
        ip.link('add', ifname=name1, peer=name2, kind='veth')


    @staticmethod
    def move_veth(machine,pid):
        from pyroute2 import IPRoute
        ip = IPRoute()
        idx = ip.link_lookup(ifname=machine)[0]
        ip.link('set',
                index=idx,
                net_ns_fd=str(pid))

    @staticmethod
    def up_network(machine,bridge,i):
        if machine == "":
            machine = "host"+str(i)
        from pyroute2 import IPRoute
        ip = IPRoute()
        idx_veth = ip.link_lookup(ifname=machine)[0]
        idx_br = ip.link_lookup(ifname='kt-'+bridge)[0]
        ip.link('set',
            index=idx_veth,
            state='up')
        ip.link('set', index=idx_veth, master=idx_br)
    
    @staticmethod
    def delete_veth(name1,name2):
        if name1 == "":
            name1 = "host"
        if name2 == "":
            name2 = "host"
        from pyroute2 import IPRoute
        ip = IPRoute()
        ip.link('del', ifname=name1, peer=name2, kind='veth')

    @staticmethod
    def create_namespace(list_container):
        subprocess.call(["sudo","mkdir","-p","/var/run/netns"])
        for container in list_container:
            pid = docker.APIClient().inspect_container(container.name)["State"]["Pid"]
            subprocess.call(["sudo","ln","-s", "/proc/"+str(pid)+"/ns/net", "/var/run/netns/"+str(pid)])
