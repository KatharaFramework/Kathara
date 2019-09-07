import tempfile
import uuid
import shutil
from model import Device
from model import Lan


class Lab(object):
	__slots__ = ['author', 'description', 'url', 'email', 'devices', 'lans', 'net_counter', 'folder_hash', 'path', 'shared_startup_path', 'shared_shutdown_path']

	def __init__(self):
		self.devices = {}
		self.lans = {}

		return

	def get_or_new_device(self, name):
		if name not in self.devices:
			self.devices[name] = Device(self, name)

		return self.devices[name]

	def get_or_new_lan(self, lan_name):
		if lan_name not in self.lans:
			self.lans[lan_name] = Lan(self, lan_name)

		return self.lans[lan_name]

	def __repr__(self):
		return "Lab(%s, %s, %s)" % (self.folder_hash, self.devices, self.lans)
