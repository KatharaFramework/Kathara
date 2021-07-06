from . import utils as setting_utils
from ....foundation.cli.ui.setting.OptionsHandler import OptionsHandler
from ....setting.addon.DockerSettingsAddon import DEFAULTS
from ....trdparty.consolemenu import *
from ....trdparty.consolemenu.items import *
from ....trdparty.consolemenu.validators.regex import RegexValidator


class DockerOptionsHandler(OptionsHandler):
    def add_items(self, current_menu, menu_formatter):
        # Hosthome Mount Option
        hosthome_string = "Automatically mount /hosthome on startup"
        hosthome_menu = SelectionMenu(strings=[],
                                      title=hosthome_string,
                                      subtitle=setting_utils.current_bool("hosthome_mount"),
                                      prologue_text="""The home directory of the current user is made available for """
                                                    """reading/writing inside the device under the special """
                                                    """directory `/hosthome`.
                                                    
                                                    Default is %s.""" %
                                                    setting_utils.format_bool(DEFAULTS['hosthome_mount']),
                                      formatter=menu_formatter
                                      )

        hosthome_menu.append_item(FunctionItem(text="Yes",
                                               function=setting_utils.update_setting_value,
                                               args=["hosthome_mount", True],
                                               should_exit=True
                                               )
                                  )
        hosthome_menu.append_item(FunctionItem(text="No",
                                               function=setting_utils.update_setting_value,
                                               args=["hosthome_mount", False],
                                               should_exit=True
                                               )
                                  )

        hosthome_item = SubmenuItem(hosthome_string, hosthome_menu, current_menu)

        # Shared Mount Option
        shared_string = "Automatically mount /shared on startup"
        shared_menu = SelectionMenu(strings=[],
                                    title=shared_string,
                                    subtitle=setting_utils.current_bool("shared_mount"),
                                    prologue_text="""The shared directory inside the lab folder is made available """
                                                  """for reading/writing inside the device under the special """
                                                  """directory `/shared`.
                                                  
                                                  Default is %s.""" %
                                                  setting_utils.format_bool(DEFAULTS['shared_mount']),
                                    formatter=menu_formatter
                                    )

        shared_menu.append_item(FunctionItem(text="Yes",
                                             function=setting_utils.update_setting_value,
                                             args=["shared_mount", True],
                                             should_exit=True
                                             )
                                )
        shared_menu.append_item(FunctionItem(text="No",
                                             function=setting_utils.update_setting_value,
                                             args=["shared_mount", False],
                                             should_exit=True
                                             )
                                )

        shared_item = SubmenuItem(shared_string, shared_menu, current_menu)

        # Multiuser Option
        multiuser_string = "Enable multiuser scenarios"
        multiuser_menu = SelectionMenu(strings=[],
                                       title=multiuser_string,
                                       subtitle=setting_utils.current_bool("multiuser"),
                                       prologue_text="""This option disables the per-user scenario creation and """
                                                     """allows to interact on the same devices and collision domains.
                                                     
                                                     Default is %s.""" %
                                                     setting_utils.format_bool(DEFAULTS['multiuser']),
                                       formatter=menu_formatter
                                       )

        multiuser_menu.append_item(FunctionItem(text="Yes",
                                                function=setting_utils.update_setting_value,
                                                args=["multiuser", True],
                                                should_exit=True
                                                )
                                   )
        multiuser_menu.append_item(FunctionItem(text="No",
                                                function=setting_utils.update_setting_value,
                                                args=["multiuser", False],
                                                should_exit=True
                                                )
                                   )

        multiuser_item = SubmenuItem(multiuser_string, multiuser_menu, current_menu)

        # Remote Docker Daemon Option
        remote_url_string = "Insert a remote Docker Daemon URL"
        remote_url_menu = SelectionMenu(strings=[],
                                        title=remote_url_string,
                                        subtitle=setting_utils.current_string("remote_url"),
                                        prologue_text="""You can specify a remote Docker Daemon URL.
                                        Default is %s.""" % DEFAULTS['remote_url'],
                                        formatter=menu_formatter
                                        )

        remote_url_menu.append_item(FunctionItem(text=remote_url_string,
                                                 function=setting_utils.read_value,
                                                 args=['remote_url',
                                                       RegexValidator(setting_utils.URL_REGEX),
                                                       'Write a Docker Daemon URL:',
                                                       'Docker Daemon URL is not a valid URL (remove '
                                                       'the trailing slash, if present)'
                                                       ],
                                                 should_exit=True
                                                 )
                                    )
        remote_url_menu.append_item(FunctionItem(text="Reset value to Empty String",
                                                 function=setting_utils.update_setting_value,
                                                 args=["remote_url", None],
                                                 should_exit=True
                                                 )
                                    )

        remote_url_item = SubmenuItem(remote_url_string, remote_url_menu, current_menu)

        # Docker Daemon TLS Path Option
        cert_path_string = "Insert a Docker Daemon TLS Cert Path"
        cert_path_menu = SelectionMenu(strings=[],
                                       title=cert_path_string,
                                       subtitle=setting_utils.current_string("cert_path"),
                                       prologue_text="""When using a remote Docker Daemon, a TLS Cert could be required.
                                       Default is %s.""" % DEFAULTS['cert_path'],
                                       formatter=menu_formatter
                                       )

        cert_path_menu.append_item(FunctionItem(text=cert_path_string,
                                                function=setting_utils.read_value,
                                                args=['cert_path',
                                                      RegexValidator(r'^.+$'),
                                                      'Write a TSL Cert Path:',
                                                      'TLS Cert Path not valid!'
                                                      ],
                                                should_exit=True
                                                )
                                   )
        cert_path_menu.append_item(FunctionItem(text="Reset value to Empty String",
                                                function=setting_utils.update_setting_value,
                                                args=["cert_path", None],
                                                should_exit=True
                                                )
                                   )

        cert_path_item = SubmenuItem(cert_path_string, cert_path_menu, current_menu)

        current_menu.append_item(hosthome_item)
        current_menu.append_item(shared_item)
        current_menu.append_item(multiuser_item)
        current_menu.append_item(remote_url_item)
        current_menu.append_item(cert_path_item)
