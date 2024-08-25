from __future__ import annotations

import json
import logging
import os
import time
from typing import Any, Dict, Optional, List

from .. import utils
from .. import version
from ..exceptions import HTTPConnectionError, SettingsError, SettingsNotFoundError, InvalidDockerConfigJsonError
from ..exceptions import InstantiationError
from ..foundation.setting.SettingsAddon import SettingsAddon
from ..foundation.setting.SettingsAddonFactory import SettingsAddonFactory
from ..webhooks.GitHubApi import GitHubApi

AVAILABLE_DEBUG_LEVELS: List[str] = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "EXCEPTION"]
AVAILABLE_MANAGERS: List[str] = ["docker", "kubernetes"]

ONE_WEEK: int = 604800

DEFAULTS: Dict[str, Any] = {
    "image": 'kathara/base',
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
SETTINGS_FILENAME = "kathara.conf"
DEFAULT_SETTINGS_PATH: str = os.path.join(utils.get_current_user_home(), ".config", SETTINGS_FILENAME)


class Setting(object):
    """Class responsible for interacting with Kathara Settings."""

    __slots__ = ['image', 'manager_type', 'terminal', 'open_terminals', 'device_shell', 'net_prefix',
                 'device_prefix', 'debug_level', 'print_startup_log', 'enable_ipv6', 'last_checked', 'addons']

    __instance: Setting = None

    @staticmethod
    def get_instance() -> Setting:
        """Return an instance of Setting.

        Returns:
            Kathara.setting.Setting: An instance of Setting.

        Raises:
            InstantiationError: If two instances of the class are created.
        """
        if Setting.__instance is None:
            Setting()

        return Setting.__instance

    def __init__(self) -> None:
        if Setting.__instance is not None:
            raise InstantiationError("This class is a singleton!")
        else:
            # Load default settings to use
            for (name, value) in DEFAULTS.items():
                setattr(self, name, value)

            self.addons: Optional[SettingsAddon] = None
            self.last_checked: float = time.time() - ONE_WEEK

            self.load_settings_addon()  # Load default addon

            Setting.__instance = self

    def __getattr__(self, item: str) -> Any:
        return self.addons.get(item)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in self.__slots__:
            super(Setting, self).__setattr__(name, value)
            return

        setattr(self.addons, name, value)

    def load_from_disk(self, path: Optional[str] = None) -> None:
        """Load settings from a specific path on disk.

        Args:
            path (Optional[str]): A path where the kathara.conf file is stored. If None, default path is used.

        Returns:
            None

        Raises:
            SettingsNotFound: If the Settings file is not found in specified path.
            SettingsError: If the specified file is not a valid JSON.
        """
        settings_path = os.path.join(path, SETTINGS_FILENAME) if path is not None else DEFAULT_SETTINGS_PATH

        if not os.path.exists(settings_path):  # Requested settings file doesn't exist, throw exception
            raise SettingsNotFoundError(settings_path)
        else:  # Requested settings file exists, read it and check values
            settings = {}
            with open(settings_path, 'r') as settings_file:
                try:
                    settings = json.load(settings_file)
                except ValueError:
                    raise SettingsError("Not a valid JSON.")

            for name, value in settings.items():
                if hasattr(self, name):
                    setattr(self, name, value)

            self.load_settings_addon()  # Manager may be changed with loaded settings, reload addon
            self.addons.load(settings)  # Load values into the addon object

    def save_to_disk(self, path: Optional[str] = None) -> None:
        """Saves settings to a kathara.conf file in the specified path on disk.

        Args:
            path (Optional[str]): A path where the kathara.conf file will be stored. If None, default path is used.

        Returns:
            None
        """
        settings_path = os.path.join(path, SETTINGS_FILENAME) if path is not None else DEFAULT_SETTINGS_PATH
        settings_dirname = os.path.dirname(settings_path)

        if not os.path.isdir(settings_dirname):  # Create folder if it doesn't exist
            os.mkdir(settings_dirname)

        to_save = self.addons.merge(self._to_dict())

        with open(settings_path, 'w') as settings_file:
            settings_file.write(json.dumps(to_save, indent=True))

        def unix_permissions():
            (uid, gid) = utils.get_current_user_uid_gid()

            os.chmod(settings_path, 0o600)
            os.chown(settings_path, uid, gid)

        # If Linux or Mac, set the right permissions and ownership to the settings file.
        utils.exec_by_platform(unix_permissions, lambda: None, unix_permissions)

    def load_from_dict(self, settings: Dict[str, Any]) -> None:
        """Load settings from a dict.

        Args:
            settings (Dict[str, Any]): A dict containing the settings name as key and its value.

        Returns:
            None
        """
        for name, value in settings.items():
            if hasattr(self, name):
                setattr(self, name, value)

        self.load_settings_addon()  # Manager may be changed with loaded settings, reload addon
        self.addons.load(settings)  # Load values into the addon object

    @staticmethod
    def wipe_from_disk() -> None:
        """Remove settings from the default settings path on disk.

        Returns:
            None
        """
        if os.path.exists(DEFAULT_SETTINGS_PATH):
            os.remove(DEFAULT_SETTINGS_PATH)

    def check(self) -> None:
        """Check if Kathara is correctly working.

        Check if the selected manager is available. Check the presence of Kathara updates.
        Check the correctness and validity of the net_prefix, device_prefix and debug level.

        Returns:
            None

        Raises:
            SettingsError: If the Networks Prefix does not contain only lowercase letters and underscore.
            SettingsError: If the Device Prefix does not contain only lowercase letters and underscore.
            SettingsError: If the Debug Level specified is not allowed.
        """
        self._check_manager()

        current_time = time.time()
        # After 1 week, check if a new Kathara version has been released.
        if current_time - self.last_checked > ONE_WEEK:
            logging.debug("Checking Updates...")
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
                self.save_to_disk()

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

    def _check_manager(self) -> None:
        """Check if the selected manager is available.

        Returns:
            None

        Raises:
            SettingsError: If the Manager Type is not allowed.
        """
        from ..manager.Kathara import Kathara
        managers = Kathara.get_available_managers_name()

        if self.manager_type not in managers.keys():
            raise SettingsError("Manager Type not allowed.")

    def check_image(self, image: str = None) -> None:
        """Check if the specified image is valid.

        Args:
            image (str): The name of the image to check. If None, check the default image.

        Returns:
            None

        Raises:
            ConnectionError: If the image is not locally available and there is no connection to a remote image repository.
            ImageNotFoundError: If the image is not found.
        """
        image = self.image if not image else image

        # Required to import here because otherwise there is a cyclic dependency
        from ..manager.Kathara import Kathara
        Kathara.get_instance().check_image(image)

    def check_terminal(self, terminal: str = None) -> bool:
        """Check that the selected terminal is available.

        Args:
            terminal (str): The selected terminal path. If None, check the availability of the default terminal.

        Returns:
            bool: True if the selected terminal is TMUX (that do not require path), else False.

        Raises:
            SettingError: If the terminal emulator specified is not found.
        """
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

    def check_docker_config_json(self, docker_config_json_path: str) -> None:
        """Check that the specified Docker Config JSON is valid.

        Args:
            docker_config_json_path (str): The path to the Docker Config JSON file.

        Returns:
            None

        Raises:
            InvalidDockerConfigJsonError: If the Docker Config JSON file is not valid.
        """
        with open(docker_config_json_path, 'r') as docker_config_json_file:
            try:
                json.load(docker_config_json_file)
            except ValueError:
                raise InvalidDockerConfigJsonError(docker_config_json_path)

    def load_settings_addon(self) -> None:
        """Load a setting addon to the base settings.

        Returns:
            None
        """
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
                "last_checked": self.last_checked
                }
