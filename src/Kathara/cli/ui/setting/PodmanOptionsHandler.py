from . import utils as setting_utils
from ....foundation.cli.ui.setting.OptionsHandler import OptionsHandler
from ....setting.addon.PodmanSettingsAddon import DEFAULTS
from ....trdparty.consolemenu import *
from ....trdparty.consolemenu.items import *
from ....trdparty.consolemenu.validators.regex import RegexValidator
from ....types import SharedCollisionDomainsOption

API_SOCKET_REGEX = r'^unix:///.+$'


class PodmanOptionsHandler(OptionsHandler):
    def add_items(self, current_menu: ConsoleMenu, menu_formatter: MenuFormatBuilder) -> None:
        # Network Plugin Option
        network_plugin_string = "Choose Podman Network Plugin"
        network_plugin_menu = SelectionMenu(
            strings=[],
            title=network_plugin_string,
            subtitle=setting_utils.current_string("network_plugin"),
            prologue_text="""Choose the Podman Network Plugin used to create collision domains.
                          
                          `katharanp_vde` plugin is based on VDE switches: a userspace switch that forwards every frame.
                          
                          `katharanp` plugin is based on Linux bridges: the data plane is in the kernel, """
                          """but LACP frames cannot cross a Linux bridge.
                          
                          Default is `%s`.""" %
                          DEFAULTS['network_plugin'],
            formatter=menu_formatter
        )

        network_plugin_menu.append_item(
            FunctionItem(
                text="katharanp_vde",
                function=setting_utils.update_setting_value,
                args=["network_plugin", "katharanp_vde"],
                should_exit=True
            )
        )
        network_plugin_menu.append_item(
            FunctionItem(
                text="katharanp",
                function=setting_utils.update_setting_value,
                args=["network_plugin", "katharanp"],
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
                          
                          On SELinux hosts, enabling this option also disables label separation """
                          """for the devices (`label=disable`), since the home directory is not relabeled.
                          
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
        image_update_policy_string = "Podman Image Update Policy"
        image_update_policy_menu = SelectionMenu(
            strings=[],
            title=image_update_policy_string,
            subtitle=setting_utils.current_string("image_update_policy"),
            prologue_text="""Choose the policy when a Podman image update is available for a running device.
                          
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
            prologue_text="""This option allows sharing collision domains between network scenarios of the same user.
                          
                          Sharing collision domains between users is not supported in rootless Podman: """
                          """each user has its own Podman, containers and networks.
                          
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
                text="Do not share collision domains",
                function=setting_utils.update_setting_value,
                args=["shared_cds", SharedCollisionDomainsOption.NOT_SHARED],
                should_exit=True
            )
        )

        shared_cds_item = SubmenuItem(shared_cds_string, shared_cds_menu, current_menu)

        # Podman API Socket Option
        api_socket_url_string = "Configure a custom local Podman socket"
        api_socket_url_menu = SelectionMenu(
            strings=[],
            title=api_socket_url_string,
            subtitle=setting_utils.current_string("api_socket_url"),
            prologue_text="""You can specify a custom local Podman socket URL """
                          """(format unix:///path/to/podman.sock), instead of the """
                          """automatically detected rootless user socket.
                          
                          Default is %s.""" % DEFAULTS['api_socket_url'],
            formatter=menu_formatter
        )

        api_socket_url_menu.append_item(
            FunctionItem(
                text=api_socket_url_string,
                function=setting_utils.update_value,
                args=['api_socket_url',
                      RegexValidator(API_SOCKET_REGEX),
                      'Write a Podman socket URL (format unix:///path/to/podman.sock):',
                      'Podman socket URL is not valid (only a `unix://` URL with an absolute '
                      'path is accepted)'
                      ],
                should_exit=True
            )
        )
        api_socket_url_menu.append_item(
            FunctionItem(
                text="Reset to default",
                function=setting_utils.update_setting_value,
                args=["api_socket_url", None],
                should_exit=True
            )
        )

        api_socket_url_item = SubmenuItem(api_socket_url_string, api_socket_url_menu, current_menu)

        current_menu.append_item(network_plugin_item)
        current_menu.append_item(hosthome_item)
        current_menu.append_item(shared_item)
        current_menu.append_item(image_update_policy_item)
        current_menu.append_item(shared_cds_item)
        current_menu.append_item(api_socket_url_item)
