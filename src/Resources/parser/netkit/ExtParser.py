import mmap
import os


class ExtParser(object):
    @staticmethod
    def parse(path):
        lab_conf_path = os.path.join(path, 'lab.conf')

        if not os.path.exists(lab_conf_path):
            raise FileNotFoundError("No lab.conf in given directory: %s\n" % path)

        # Reads lab.conf in memory so it is faster.
        with open(lab_conf_path, 'r') as lab_file:
            lab_mem_file = mmap.mmap(lab_file.fileno(), 0, access=mmap.ACCESS_READ)

        # Check if collision domain exists
        # Check if interface exists

        # if eth0 => add eth0 to bridge
        # if eth0.VLAN =>
        #   $(ip link add link $PREFIX_INTERFACE name $INTERFACE type vlan id $VLAN)
        #   $(ip link set dev $INTERFACE up)
        #   $(brctl addif br-$BRCTL_NET $INTERFACE)

        # Clean