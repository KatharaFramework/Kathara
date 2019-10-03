import json
import os
import time

from .. import utils
from .. import version
from ..api.GitHubApi import GitHubApi

MAX_DOCKER_LAN_NUMBER = 256 * 256
MAX_K8S_NUMBER = (1 << 24) - 20

DOCKER = "docker"
K8S = "k8s"

ONE_WEEK = 604800

SETTING_PATH = os.path.join(os.path.expanduser('~'), ".kathara.config")


class Setting(object):
    __slots__ = ['image', 'deployer_type', 'net_counter', 'terminal', 'open_terminals',
                 'hosthome_mount', 'machine_shell', 'net_prefix', 'machine_prefix', 'last_checked', 'vlab_folder_name']

    __instance = None

    @staticmethod
    def get_instance():
        if Setting.__instance is None:
            Setting()

        return Setting.__instance

    def __init__(self):
        if Setting.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            # Default values to use
            self.image = 'kathara/netkit_base'
            self.deployer_type = 'docker'
            self.net_counter = 0
            self.terminal = '/usr/bin/xterm' #TODO: thinking about changing to x-terminal-emulator that is a symlink to the default terminal
            self.open_terminals = True
            self.hosthome_mount = True
            self.machine_shell = "bash"
            self.net_prefix = 'kathara'
            self.machine_prefix = 'kathara'
            self.vlab_folder_name = "kathara_vlab"
            self.last_checked = time.time() - ONE_WEEK

            self.load()

            Setting.__instance = self

    def load(self):
        if not os.path.exists(SETTING_PATH):               # If settings file don't exist, create with defaults
            self.save()
        else:                                                   # If file exists, read it and check values
            settings = {}
            with open(SETTING_PATH, 'r') as settings_file:
                try:
                    settings = json.load(settings_file)
                except ValueError:
                    raise Exception("Settings file is not a valid JSON. Fix it or delete it before launching.")

            for (name, value) in settings.items():
                setattr(self, name, value)

    @staticmethod
    def wipe():
        if os.path.exists(SETTING_PATH):
            os.remove(SETTING_PATH)

        Setting.__instance = None
        Setting.get_instance()


    def save(self, content=None):
        """
        Saves settings to a config.json file in the Kathara path.
        :param content: If None, current object settings are saved. If a dict is passed, the dict is saved.
        """
        to_save = self._to_dict() if content is None else content

        with open(SETTING_PATH, 'w') as settings_file:
            settings_file.write(json.dumps(to_save, indent=True))

    def save_selected(self, selected_settings):
        """
        Saves only the selected settings, the other ones are kept as the current config.json file.
        :param selected_settings: List of selected settings to save into the JSON
        """
        settings = {}

        # Open the original JSON file and read it
        with open(SETTING_PATH, 'r') as settings_file:
            try:
                settings = json.load(settings_file)
            except ValueError:
                raise Exception("Settings file is not a valid JSON. Fix it or delete it before launching.")

        # Assign to the JSON settings the desired ones
        for setting_name in selected_settings:
            settings[setting_name] = getattr(self, setting_name)

        # Save new settings
        self.save(content=settings)

    def check(self):
        if self.deployer_type not in [DOCKER, K8S]:
            raise Exception("Deployer Type not allowed.")

        from ..manager.ManagerProxy import ManagerProxy
        try:
            ManagerProxy.get_instance().check_image(self.image)
        except Exception as e:
            raise Exception(str(e))

        current_time = time.time()
        # After 1 week, check if a new image version has been released.
        if current_time - self.last_checked > ONE_WEEK:
            print(utils.format_headers("Checking Updates"))

            latest_remote_release = GitHubApi.get_release_information()
            latest_version = latest_remote_release["tag_name"]

            if version.less_than(version.CURRENT_VERSION, latest_version):
                print("A new version of Kathara has been released.")
                print("Current: %s - Latest: %s" % (version.CURRENT_VERSION, latest_version))
                print("Please update it with `pip install kathara`")

            if self.deployer_type == DOCKER:
                ManagerProxy.get_instance().check_updates(self)

                self.last_checked = current_time
                self.save_selected(['last_checked'])

            print("=============================================================")

        try:
            self.net_counter = int(self.net_counter)
            self.check_net_counter()
        except ValueError:
            raise Exception("Network Counter must be an integer.")

    def inc_net_counter(self):
        self.net_counter += 1

        if (self.deployer_type == DOCKER and self.net_counter > MAX_DOCKER_LAN_NUMBER) or \
           (self.deployer_type == K8S and self.net_counter > MAX_K8S_NUMBER):
            self.net_counter = 0

    def check_net_counter(self):
        if self.net_counter < 0:
            raise Exception("Network Counter must be greater or equal than zero.")
        else:
            if self.deployer_type == DOCKER and self.net_counter > MAX_DOCKER_LAN_NUMBER:
                raise Exception("Network Counter must be lesser than %d." % MAX_DOCKER_LAN_NUMBER)
            elif self.deployer_type == K8S and self.net_counter > MAX_K8S_NUMBER:
                raise Exception("Network Counter must be lesser than %d." % MAX_K8S_NUMBER)

    def _to_dict(self):
        return {"image": self.image,
                "deployer_type": self.deployer_type,
                "net_counter": self.net_counter,
                "terminal": self.terminal,
                "open_terminals": self.open_terminals,
                "hosthome_mount": self.hosthome_mount,
                "machine_shell": self.machine_shell,
                "net_prefix": self.net_prefix,
                "machine_prefix": self.machine_prefix,
                "vlab_folder_name" : self.vlab_folder_name,
                "last_checked": self.last_checked
                }
