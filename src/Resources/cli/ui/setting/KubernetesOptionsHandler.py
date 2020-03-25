from . import utils as setting_utils
from ....foundation.cli.ui.setting.OptionsHandler import OptionsHandler
from ....setting.addon.KubernetesSettingsAddon import DEFAULTS
from ....trdparty.consolemenu import *
from ....trdparty.consolemenu.items import *
from ....trdparty.consolemenu.validators.regex import RegexValidator

url_regex = r'^(?:http)s?://'  # http:// or https://
r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
r'localhost|'  # localhost...
r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
r'(?::\d+)?'  # optional port
r'(?:/?|[/?]\S+)$'


class KubernetesOptionsHandler(OptionsHandler):
    def add_items(self, current_menu, menu_formatter):
        # API URL Option
        api_server_url_string = "Insert a Kubernetes API Server URL"
        api_server_url_menu = SelectionMenu(strings=[],
                                            title=api_server_url_string,
                                            subtitle=setting_utils.current_string("api_server_url"),
                                            prologue_text="""You can specify a remote Kubernetes API Server URL to """
                                                          """connect to when Kathara is not used on a Kubernetes """
                                                          """master.
                                                          Default is %s.""" % DEFAULTS['api_server_url'],
                                            formatter=menu_formatter
                                            )

        api_server_url_menu.append_item(FunctionItem(text=api_server_url_string,
                                                     function=setting_utils.read_value,
                                                     args=['api_server_url',
                                                           RegexValidator(url_regex),
                                                           'Write a Kubernetes API Server URL:',
                                                           'Kubernetes API Server URL is not a valid URL!'
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
                                                      RegexValidator(r'^\w+$'),
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
                                         prologue_text="""Each Kubernetes host creates a /home/shared directory """
                                                       """and it is made available for reading/writing inside """
                                                       """the device under the special directory `/shared`.
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

        current_menu.append_item(api_url_item)
        current_menu.append_item(api_token_item)
        current_menu.append_item(host_shared_item)
