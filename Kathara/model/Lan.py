
class Lan(object):
	__slots__ = ['lab','name','net_ifaces']

	def __init__(self, lab, name):
		self.lab = lab
		self.name = name
		self.net_ifaces = {}
		return

	def add_interface(self, device, interface_name):
		self.devices_to_interfaces[device] = interface_name

	def get_name(self):
		return "lan-%s" % self.name.lower()

	def __repr__(self):
		return "Lan(%s, %s)" % (self.name, self.devices_to_interfaces)
