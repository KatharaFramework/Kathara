import sys

def move_veth(machine,pid):
    from pyroute2 import IPRoute
    ip = IPRoute()
    idx = ip.link_lookup(ifname=machine)[0]
    ip.link('set',
            index=idx,
            net_ns_fd=pid)

move_veth(sys.argv[1],sys.argv[2])