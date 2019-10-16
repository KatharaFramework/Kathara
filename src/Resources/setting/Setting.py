import json
import logging
import os
import time

from .. import utils
from .. import version
from ..api.GitHubApi import GitHubApi
from ..exceptions import HTTPConnectionError, SettingsError

MAX_K8S_NUMBER = (1 << 24) - 20

DOCKER = "docker"
K8S = "k8s"

POSSIBLE_SHELLS = ["/bin/bash", "/bin/sh", "/bin/ash", "/bin/ksh", "/bin/zsh", "/bin/fish", "/bin/csh", "/bin/tcsh"]
POSSIBLE_DEBUG_LEVELS = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
POSSIBLE_MANAGERS = ["docker"]

ONE_WEEK = 604800

SETTING_FOLDER = None
SETTING_PATH = None
EXCLUDED_FILES = ['.DS_Store']
EXCLUDED_IMAGES = ['megalos-bgp-manager']


class Setting(object):
    __slots__ = ['image', 'manager_type', 'terminal', 'open_terminals',
                 'hosthome_mount', 'machine_shell', 'net_prefix', 'machine_prefix', 'debug_level',
                 'print_startup_log', 'last_checked']

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
            global SETTING_FOLDER, SETTING_PATH
            SETTING_FOLDER = os.path.join(utils.get_current_user_home(), ".config")
            SETTING_PATH = os.path.join(SETTING_FOLDER, "kathara.conf")

            # Default values to use
            self.image = 'kathara/quagga'
            self.manager_type = 'docker'
            self.terminal = '/usr/bin/xterm'
            self.open_terminals = True
            self.hosthome_mount = False
            self.machine_shell = "/bin/bash"
            self.net_prefix = 'kathara'
            self.machine_prefix = 'kathara'
            self.debug_level = "INFO"
            self.print_startup_log = True
            self.last_checked = time.time() - ONE_WEEK

            self.load()

            Setting.__instance = self

    def load(self):
        if not os.path.exists(SETTING_PATH):                    # If settings file don't exist, create with defaults
            if not os.path.isdir(SETTING_FOLDER):               # Create .config folder if doesn't exists, create it
                os.mkdir(SETTING_FOLDER)

            self.save()

            def unix_permissions():
                (uid, gid) = utils.get_current_user_uid_gid()

                os.chmod(SETTING_PATH, 0o600)
                os.chown(SETTING_PATH, uid, gid)

            # If Linux or Mac, set the right permissions and ownership to the settings file.
            utils.exec_by_platform(unix_permissions, lambda: None, unix_permissions)
        else:                                                   # If file exists, read it and check values
            settings = {}
            with open(SETTING_PATH, 'r') as settings_file:
                try:
                    settings = json.load(settings_file)
                except ValueError:
                    raise SettingsError("Not a valid JSON.")

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
                raise SettingsError("Not a valid JSON.")

        # Assign to the JSON settings the desired ones
        for setting_name in selected_settings:
            settings[setting_name] = getattr(self, setting_name)

        # Save new settings
        self.save(content=settings)

    def check(self):
        self.check_manager()

        self.check_image()

        current_time = time.time()
        # After 1 week, check if a new image and Kathara version has been released.
        if current_time - self.last_checked > ONE_WEEK:
            logging.debug(utils.format_headers("Checking Updates"))
            checked = True

            try:
                logging.debug("Checking Kathara release...")

                latest_remote_release = GitHubApi.get_release_information()
                latest_version = latest_remote_release["tag_name"]

                if version.less_than(version.CURRENT_VERSION, latest_version):
                    print("A new version of Kathara has been released.")
                    print("Current: %s - Latest: %s" % (version.CURRENT_VERSION, latest_version))
                    print("Please update it from https://github.com/KatharaFramework/Kathara")
            except HTTPConnectionError:
                logging.debug("Connection to GitHub failed, passing...")
                checked = False

            if self.manager_type == DOCKER:
                logging.debug("Checking Docker Image version...")

                try:
                    from ..manager.ManagerProxy import ManagerProxy
                    ManagerProxy.get_instance().check_updates(self)
                except HTTPConnectionError:
                    logging.debug("Connection to DockerHub failed, passing...")
                    checked = False

            if checked:
                self.last_checked = current_time
                self.save_selected(['last_checked'])

            logging.debug("=============================================================")

        try:
            utils.re_search_fail(r"^[a-z]+_?[a-z_]+$", self.net_prefix)
        except ValueError:
            raise SettingsError("Networks Prefix must only contain lowercase letters and underscore.")

        try:
            utils.re_search_fail(r"^[a-z]+_?[a-z_]+$", self.machine_prefix)
        except ValueError:
            raise SettingsError("Machine Prefix must only contain lowercase letters and underscore.")

        if self.debug_level not in POSSIBLE_DEBUG_LEVELS:
            raise SettingsError("Debug Level must be one of the following: %s." % (", ".join(POSSIBLE_DEBUG_LEVELS)))

    def check_manager(self):
        from ..manager.ManagerProxy import ManagerProxy
        managers = ManagerProxy.get_available_managers_name()

        if self.manager_type not in managers.keys():
            raise SettingsError("Manager Type not allowed.")

    def check_image(self, image=None):
        image = self.image if not image else image

        # Required to import here because otherwise there is a cyclic dependency
        from ..manager.ManagerProxy import ManagerProxy
        ManagerProxy.get_instance().check_image(image)

    def _to_dict(self):
        return {"image": self.image,
                "manager_type": self.manager_type,
                "terminal": self.terminal,
                "open_terminals": self.open_terminals,
                "hosthome_mount": self.hosthome_mount,
                "machine_shell": self.machine_shell,
                "net_prefix": self.net_prefix,
                "machine_prefix": self.machine_prefix,
                "debug_level": self.debug_level,
                "print_startup_log": self.print_startup_log,
                "last_checked": self.last_checked
                }
