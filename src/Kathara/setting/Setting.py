from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict

from .. import utils
from .. import version
from ..connectors.GitHubApi import GitHubApi
from ..exceptions import HTTPConnectionError, SettingsError
from ..foundation.setting.SettingsAddonFactory import SettingsAddonFactory
from ...foundation.setting.SettingsAddon import SettingsAddon

AVAILABLE_DEBUG_LEVELS = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "EXCEPTION"]
AVAILABLE_MANAGERS = ["docker", "kubernetes"]

ONE_WEEK = 604800

DEFAULTS = {
    "image": 'kathara/quagga',
    "manager_type": 'docker',
    "terminal": utils.exec_by_platform(lambda: '/usr/bin/xterm', lambda: '', lambda: 'Terminal'),
    "open_terminals": True,
    "device_shell": '/bin/bash',
    "net_prefix": 'kathara',
    "device_prefix": 'kathara',
    "debug_level": 'INFO',
    "print_startup_log": True,
    "enable_ipv6": False
}


class Setting(object):
    __slots__ = ['image', 'manager_type', 'terminal', 'open_terminals', 'device_shell', 'net_prefix',
                 'device_prefix', 'debug_level', 'print_startup_log', 'enable_ipv6', 'last_checked', 'addons']

    SETTING_FOLDER: str = None
    SETTING_PATH: str = None

    __instance: Setting = None

    @staticmethod
    def get_instance() -> Setting:
        if Setting.__instance is None:
            Setting()

        return Setting.__instance

    def __init__(self) -> None:
        if Setting.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            Setting.SETTING_FOLDER = os.path.join(utils.get_current_user_home(), ".config")
            Setting.SETTING_PATH = os.path.join(Setting.SETTING_FOLDER, "kathara.conf")

            # Load default settings to use
            for (name, value) in DEFAULTS.items():
                setattr(self, name, value)

            self.addons: SettingsAddon = None
            self.last_checked: float = time.time() - ONE_WEEK

            self.load()

            Setting.__instance = self

    def __getattr__(self, item: str) -> Any:
        return self.addons.get(item)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in self.__slots__:
            super(Setting, self).__setattr__(name, value)
            return

        setattr(self.addons, name, value)

    def load(self) -> None:
        if not os.path.exists(Setting.SETTING_PATH):  # If settings file don't exist, create with defaults
            if not os.path.isdir(Setting.SETTING_FOLDER):  # Create .config folder if doesn't exists, create it
                os.mkdir(Setting.SETTING_FOLDER)

            self.load_settings_addon()  # Load default manager addons
            self.save()

            def unix_permissions():
                (uid, gid) = utils.get_current_user_uid_gid()

                os.chmod(Setting.SETTING_PATH, 0o600)
                os.chown(Setting.SETTING_PATH, uid, gid)

            # If Linux or Mac, set the right permissions and ownership to the settings file.
            utils.exec_by_platform(unix_permissions, lambda: None, unix_permissions)
        else:  # If file exists, read it and check values
            settings = {}
            with open(Setting.SETTING_PATH, 'r') as settings_file:
                try:
                    settings = json.load(settings_file)
                except ValueError:
                    raise SettingsError("Not a valid JSON.")

            for name, value in settings.items():
                if hasattr(self, name):
                    setattr(self, name, value)

            self.load_settings_addon()  # Manager may be changed with loaded settings, reload addon
            self.addons.load(settings)  # Load values into the addon object

    @staticmethod
    def wipe() -> None:
        if os.path.exists(Setting.SETTING_PATH):
            os.remove(Setting.SETTING_PATH)

    def save(self) -> None:
        """
        Saves settings to a config.json file in the Kathara path.
        """
        to_save = self.addons.merge(self._to_dict())

        with open(Setting.SETTING_PATH, 'w') as settings_file:
            settings_file.write(json.dumps(to_save, indent=True))

    def check(self) -> None:
        self.check_manager()

        self.check_terminal()

        current_time = time.time()
        # After 1 week, check if a new Kathara version has been released.
        if current_time - self.last_checked > ONE_WEEK:
            logging.debug(utils.format_headers("Checking Updates"))
            checked = True

            try:
                logging.debug("Checking Kathara release...")

                latest_remote_release = GitHubApi.get_release_information()
                latest_version = latest_remote_release["tag_name"]

                if version.less_than(version.CURRENT_VERSION, latest_version):
                    logging.info("A new version of Kathara has been released.")
                    logging.info("Current: %s - Latest: %s" % (version.CURRENT_VERSION, latest_version))
                    logging.info("Please update it from https://github.com/KatharaFramework/Kathara")
            except HTTPConnectionError:
                logging.debug("Connection to GitHub failed, passing...")
                checked = False

            if checked:
                self.last_checked = current_time
                self.save()

            logging.debug(utils.format_headers())

        try:
            utils.re_search_fail(r"^[a-z]+_?[a-z_]+$", self.net_prefix)
        except ValueError:
            raise SettingsError("Networks Prefix must only contain lowercase letters and underscore.")

        try:
            utils.re_search_fail(r"^[a-z]+_?[a-z_]+$", self.device_prefix)
        except ValueError:
            raise SettingsError("Device Prefix must only contain lowercase letters and underscore.")

        if self.debug_level not in AVAILABLE_DEBUG_LEVELS:
            raise SettingsError("Debug Level must be one of the following: %s." % (", ".join(AVAILABLE_DEBUG_LEVELS)))

    def check_manager(self) -> None:
        from ..manager.Kathara import Kathara
        managers = Kathara.get_available_managers_name()

        if self.manager_type not in managers.keys():
            raise SettingsError("Manager Type not allowed.")

    def check_image(self, image: str = None) -> None:
        image = self.image if not image else image

        # Required to import here because otherwise there is a cyclic dependency
        from ..manager.Kathara import Kathara
        Kathara.get_instance().check_image(image)

    def check_terminal(self, terminal: str = None) -> bool:
        terminal = self.terminal if not terminal else terminal

        # Skip check for TMUX (special value)
        if terminal == "TMUX":
            return True

        def check_unix():
            return os.path.isfile(terminal) and os.access(terminal, os.X_OK)

        def check_osx():
            import appscript
            import aem
            try:
                appscript.app(terminal)
            except aem.findapp.ApplicationNotFoundError:
                return False

            return True

        if not utils.exec_by_platform(check_unix, lambda: True, check_osx):
            raise SettingsError("Terminal Emulator `%s` not valid! Install it before using it." % terminal)

        return True

    def load_settings_addon(self) -> None:
        self.addons = SettingsAddonFactory().create_instance(class_args=(self.manager_type.capitalize(),))

    def _to_dict(self) -> Dict[str, Any]:
        return {"image": self.image,
                "manager_type": self.manager_type,
                "terminal": self.terminal,
                "open_terminals": self.open_terminals,
                "device_shell": self.device_shell,
                "net_prefix": self.net_prefix,
                "device_prefix": self.device_prefix,
                "debug_level": self.debug_level,
                "print_startup_log": self.print_startup_log,
                "enable_ipv6": self.enable_ipv6,
                "last_checked": self.last_checked,
                }
