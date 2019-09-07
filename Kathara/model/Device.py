
class Device(object):
	__slots__ = ['lab','name','startup_path','shutdown_path','folder','interfaces','meta']

	def __init__(self, lab, name):
		self.lab = lab
		self.name = name

		self.interfaces = {}
		self.meta = {}
		return

	def add_meta(self, name, value):
		self.meta[name] = value

	def get_interface_by_number(self, number):
		if number in self.interfaces:
			return self.interfaces[number]

		raise Exception("Interface `%s` not found on device `%s`." % (number, self.name))

	def __repr__(self):
		return "Device(%s, %s)" % (self.name, self.interfaces)
