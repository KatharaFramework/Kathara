from . import utils as setting_utils
from ....foundation.cli.ui.setting.OptionsHandler import OptionsHandler
from ....setting.addon.DockerSettingsAddon import DEFAULTS
from ....trdparty.consolemenu import *
from ....trdparty.consolemenu.items import *
from ....trdparty.consolemenu.validators.regex import RegexValidator
from ....types import SharedCollisionDomainsOption
from ....utils import exec_by_platform


class DockerOptionsHandler(OptionsHandler):
    def add_items(self, current_menu: ConsoleMenu, menu_formatter: MenuFormatBuilder) -> None:
        # Network Plugin Option
        network_plugin_string = "Choose Docker Network Plugin version"
        network_plugin_menu = SelectionMenu(
            strings=[],
            title=network_plugin_string,
            subtitle=setting_utils.current_string("network_plugin"),
            prologue_text="""Choose Docker Network Plugin version for collision domains.
                          
                          `kathara/katharanp` plugin is based on Linux bridges.
                          
                          `kathara/katharanp_vde` plugin is based on VDE switches.

                          Default is `%s`.""" %
                          DEFAULTS['network_plugin'],
            formatter=menu_formatter
        )

        network_plugin_menu.append_item(
            FunctionItem(
                text="kathara/katharanp",
                function=setting_utils.update_setting_value,
                args=["network_plugin", "kathara/katharanp"],
                should_exit=True
            )
        )
        network_plugin_menu.append_item(
            FunctionItem(
                text="kathara/katharanp_vde",
                function=setting_utils.update_setting_value,
                args=["network_plugin", "kathara/katharanp_vde"],
                should_exit=True
            )
        )

        network_plugin_item = SubmenuItem(network_plugin_string, network_plugin_menu, current_menu)

        # Hosthome Mount Option
        hosthome_string = "Automatically mount /hosthome on startup"
        hosthome_menu = SelectionMenu(
            strings=[],
            title=hosthome_string,
            subtitle=setting_utils.current_bool("hosthome_mount"),
            prologue_text="""The home directory of the current user is made available for """
                          """reading/writing inside the device under the special directory `/hosthome`.
                          
                          Default is %s.""" %
                          setting_utils.format_bool(DEFAULTS['hosthome_mount']),
            formatter=menu_formatter
        )

        hosthome_menu.append_item(
            FunctionItem(
                text="Yes",
                function=setting_utils.update_setting_value,
                args=["hosthome_mount", True],
                should_exit=True
            )
        )
        hosthome_menu.append_item(
            FunctionItem(
                text="No",
                function=setting_utils.update_setting_value,
                args=["hosthome_mount", False],
                should_exit=True
            )
        )

        hosthome_item = SubmenuItem(hosthome_string, hosthome_menu, current_menu)

        # Shared Mount Option
        shared_string = "Automatically mount /shared on startup"
        shared_menu = SelectionMenu(
            strings=[],
            title=shared_string,
            subtitle=setting_utils.current_bool("shared_mount"),
            prologue_text="""The shared directory inside the network scenario folder is """
                          """made available for reading/writing inside the device under the special directory `/shared`.
                          
                          Default is %s.""" %
                          setting_utils.format_bool(DEFAULTS['shared_mount']),
            formatter=menu_formatter
        )

        shared_menu.append_item(
            FunctionItem(
                text="Yes",
                function=setting_utils.update_setting_value,
                args=["shared_mount", True],
                should_exit=True
            )
        )
        shared_menu.append_item(
            FunctionItem(
                text="No",
                function=setting_utils.update_setting_value,
                args=["shared_mount", False],
                should_exit=True
            )
        )

        shared_item = SubmenuItem(shared_string, shared_menu, current_menu)

        # Image Update Policy Option
        image_update_policy_string = "Docker Image Update Policy"
        image_update_policy_menu = SelectionMenu(
            strings=[],
            title=image_update_policy_string,
            subtitle=setting_utils.current_string("image_update_policy"),
            prologue_text="""Choose the policy when a Docker image update is available for a running device.             
  
                          \tDefault is %s.""" % DEFAULTS['image_update_policy'],
            formatter=menu_formatter
        )

        image_update_policy_menu.append_item(
            FunctionItem(
                text="Prompt",
                function=setting_utils.update_setting_value,
                args=["image_update_policy", "Prompt"],
                should_exit=True
            )
        )
        image_update_policy_menu.append_item(
            FunctionItem(
                text="Always",
                function=setting_utils.update_setting_value,
                args=["image_update_policy", "Always"],
                should_exit=True
            )
        )
        image_update_policy_menu.append_item(
            FunctionItem(
                text="Never",
                function=setting_utils.update_setting_value,
                args=["image_update_policy", "Never"],
                should_exit=True
            )
        )

        image_update_policy_item = SubmenuItem(image_update_policy_string, image_update_policy_menu, current_menu)

        # Shared Collision Domains Option
        shared_cds_string = "Enable Shared Collision Domains"
        shared_cds_menu = SelectionMenu(
            strings=[],
            title=shared_cds_string,
            subtitle=setting_utils.current_enum("shared_cds", SharedCollisionDomainsOption.to_string),
            prologue_text="""This option allows sharing collision domains between network scenarios and users.
                          
                          Default is: %s.""" % SharedCollisionDomainsOption.to_string(DEFAULTS['shared_cds']),
            formatter=menu_formatter
        )

        shared_cds_menu.append_item(
            FunctionItem(
                text="Share collision domains between network scenarios",
                function=setting_utils.update_setting_value,
                args=["shared_cds", SharedCollisionDomainsOption.LABS],
                should_exit=True
            )
        )
        shared_cds_menu.append_item(
            FunctionItem(
                text="Share collision domains between users",
                function=setting_utils.update_setting_value,
                args=["shared_cds", SharedCollisionDomainsOption.USERS],
                should_exit=True
            )
        )

        shared_cds_menu.append_item(
            FunctionItem(
                text="Do not share collision domains",
                function=setting_utils.update_setting_value,
                args=["shared_cds", SharedCollisionDomainsOption.NOT_SHARED],
                should_exit=True
            )
        )

        shared_cds_item = SubmenuItem(shared_cds_string, shared_cds_menu, current_menu)

        # Remote Docker Daemon Option
        def remote_url_unix():
            remote_url_string = "Configure a remote Docker connection"
            remote_url_menu = SelectionMenu(
                strings=[],
                title=remote_url_string,
                subtitle=setting_utils.current_string("remote_url"),
                prologue_text="""You can specify a remote Docker Daemon URL.
                                            
                              Default is %s.""" % DEFAULTS['remote_url'],
                formatter=menu_formatter
            )

            remote_url_menu.append_item(
                FunctionItem(
                    text="Insert a remote Docker Daemon URL",
                    function=setting_utils.update_value,
                    args=['remote_url',
                          RegexValidator(setting_utils.URL_REGEX),
                          'Write a Docker Daemon URL '
                          '(format http[s]://<remote-url>:<remote-port>):',
                          'Docker Daemon URL is not a valid URL (remove '
                          'the trailing slash, if present)'
                          ],
                    should_exit=False
                )
            )

            remote_url_item = SubmenuItem(remote_url_string, remote_url_menu, current_menu)

            # Docker Daemon TLS Path Option
            cert_path_string = "Configure a Docker Daemon TLS Cert Path"
            cert_path_menu = SelectionMenu(
                strings=[],
                title=cert_path_string,
                subtitle=setting_utils.current_string("cert_path"),
                prologue_text="""When using a remote Docker Daemon, a TLS Cert could be required.
                              
                              Default is %s.""" % DEFAULTS['cert_path'],
                formatter=menu_formatter
            )

            cert_path_menu.append_item(
                FunctionItem(
                    text="Insert a Docker Daemon TLS Cert Path",
                    function=setting_utils.update_value,
                    args=['cert_path',
                          RegexValidator(r'^.+$'),
                          'Write a TSL Cert Path:',
                          'TLS Cert Path not valid!'
                          ],
                    should_exit=False
                )
            )
            cert_path_menu.append_item(
                FunctionItem(
                    text="Reset value to Empty String",
                    function=setting_utils.update_setting_value,
                    args=["cert_path", None],
                    should_exit=False
                )
            )

            cert_path_item = SubmenuItem(cert_path_string, cert_path_menu, remote_url_menu)
            remote_url_menu.append_item(cert_path_item)

            remote_url_menu.append_item(
                FunctionItem(
                    text="Reset remote Docker connection to default",
                    function=setting_utils.update_setting_values,
                    args=[[("remote_url", None), ("cert_path", None)]],
                    should_exit=False
                )
            )

            return remote_url_item

        platform_remote_url_item = exec_by_platform(remote_url_unix, lambda: None, remote_url_unix)

        current_menu.append_item(network_plugin_item)
        current_menu.append_item(hosthome_item)
        current_menu.append_item(shared_item)
        current_menu.append_item(image_update_policy_item)
        current_menu.append_item(shared_cds_item)
        if platform_remote_url_item:
            current_menu.append_item(platform_remote_url_item)
