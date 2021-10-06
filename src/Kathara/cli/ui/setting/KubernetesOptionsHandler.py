from . import utils as setting_utils
from ....foundation.cli.ui.setting.OptionsHandler import OptionsHandler
from ....setting.addon.KubernetesSettingsAddon import DEFAULTS
from ....trdparty.consolemenu import *
from ....trdparty.consolemenu.items import *
from ....trdparty.consolemenu.validators.regex import RegexValidator


class KubernetesOptionsHandler(OptionsHandler):
    def add_items(self, current_menu: ConsoleMenu, menu_formatter: MenuFormatBuilder) -> None:
        # API URL Option
        api_server_url_string = "Insert a Kubernetes API Server URL"
        api_server_url_menu = SelectionMenu(strings=[],
                                            title=api_server_url_string,
                                            subtitle=setting_utils.current_string("api_server_url"),
                                            prologue_text="""You can specify a remote Kubernetes API Server URL to """
                                                          """connect to when Megalos is not used on a Kubernetes """
                                                          """master.
                                                          Default is %s.""" % DEFAULTS['api_server_url'],
                                            formatter=menu_formatter
                                            )

        api_server_url_menu.append_item(FunctionItem(text=api_server_url_string,
                                                     function=setting_utils.read_value,
                                                     args=['api_server_url',
                                                           RegexValidator(setting_utils.URL_REGEX),
                                                           'Write a Kubernetes API Server URL:',
                                                           'Kubernetes API Server URL is not a valid URL (remove '
                                                           'the trailing slash, if present)'
                                                           ],
                                                     should_exit=True
                                                     )
                                        )
        api_server_url_menu.append_item(FunctionItem(text="Reset value to Empty String",
                                                     function=setting_utils.update_setting_value,
                                                     args=["api_server_url", None],
                                                     should_exit=True
                                                     )
                                        )

        api_url_item = SubmenuItem(api_server_url_string, api_server_url_menu, current_menu)

        # API Token Option
        api_token_string = "Insert a Kubernetes API Token"
        api_token_menu = SelectionMenu(strings=[],
                                       title=api_token_string,
                                       prologue_text="""When using a remote Kubernetes API Server, you must also """
                                                     """specify the authentication token to use.
                                                     Default is %s.""" % DEFAULTS['api_token'],
                                       formatter=menu_formatter
                                       )

        api_token_menu.append_item(FunctionItem(text=api_token_string,
                                                function=setting_utils.read_value,
                                                args=['api_token',
                                                      RegexValidator(r'^.+$'),
                                                      'Write a Kubernetes API Token:',
                                                      'Kubernetes API Token not valid!'
                                                      ],
                                                should_exit=True
                                                )
                                   )
        api_token_menu.append_item(FunctionItem(text="Reset value to Empty String",
                                                function=setting_utils.update_setting_value,
                                                args=["api_token", None],
                                                should_exit=True
                                                )
                                   )

        api_token_item = SubmenuItem(api_token_string, api_token_menu, current_menu)

        # Shared Mount Option
        host_shared_string = "Automatically mount /shared on startup"
        host_shared_menu = SelectionMenu(strings=[],
                                         title=host_shared_string,
                                         subtitle=setting_utils.current_bool("host_shared"),
                                         prologue_text="""Each Kubernetes worker node creates a /home/shared """
                                                       """directory and it is made available for reading/writing """
                                                       """inside the device under the special directory `/shared`.
                                                       Default is %s.""" %
                                                       setting_utils.format_bool(DEFAULTS['host_shared']),
                                         formatter=menu_formatter
                                         )

        host_shared_menu.append_item(FunctionItem(text="Yes",
                                                  function=setting_utils.update_setting_value,
                                                  args=["host_shared", True],
                                                  should_exit=True
                                                  )
                                     )
        host_shared_menu.append_item(FunctionItem(text="No",
                                                  function=setting_utils.update_setting_value,
                                                  args=["host_shared", False],
                                                  should_exit=True
                                                  )
                                     )

        host_shared_item = SubmenuItem(host_shared_string, host_shared_menu, current_menu)

        # Image Pull Policy Option
        image_pull_policy_string = "Image Pull Policy"
        image_pull_policy_menu = SelectionMenu(strings=[],
                                               title=image_pull_policy_string,
                                               subtitle=setting_utils.current_string("image_pull_policy"),
                                               prologue_text="""Specify the image pull policy for Docker images """
                                                             """used by devices. 
                                                             Default is %s.""" % DEFAULTS['image_pull_policy'],
                                               formatter=menu_formatter
                                               )

        image_pull_policy_menu.append_item(FunctionItem(text="Always",
                                                        function=setting_utils.update_setting_value,
                                                        args=["image_pull_policy", "Always"],
                                                        should_exit=True
                                                        )
                                           )
        image_pull_policy_menu.append_item(FunctionItem(text="If Not Present",
                                                        function=setting_utils.update_setting_value,
                                                        args=["image_pull_policy", "IfNotPresent"],
                                                        should_exit=True
                                                        )
                                           )
        image_pull_policy_menu.append_item(FunctionItem(text="Never",
                                                        function=setting_utils.update_setting_value,
                                                        args=["image_pull_policy", "Never"],
                                                        should_exit=True
                                                        )
                                           )

        image_pull_policy_item = SubmenuItem(image_pull_policy_string, image_pull_policy_menu, current_menu)

        current_menu.append_item(api_url_item)
        current_menu.append_item(api_token_item)
        current_menu.append_item(host_shared_item)
        current_menu.append_item(image_pull_policy_item)
