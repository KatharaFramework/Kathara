import sys

def up_network(name,bridge):
    from pyroute2 import IPRoute
    ip = IPRoute()
    idx_veth = ip.link_lookup(ifname=name)[0]
    idx_br = ip.link_lookup(ifname='kt-'+bridge)[0]
    ip.link('set',
            index=idx_veth,
            state='up')
    ip.link('set', index=idx_veth, master=idx_br)

up_network(sys.argv[1],sys.argv[2])
