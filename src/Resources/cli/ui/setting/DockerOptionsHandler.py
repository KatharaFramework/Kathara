from . import utils as setting_utils
from ....foundation.cli.ui.setting.OptionsHandler import OptionsHandler
from ....setting.addon.DockerSettingsAddon import DEFAULTS
from ....trdparty.consolemenu import *
from ....trdparty.consolemenu.items import *


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

        current_menu.append_item(hosthome_item)
        current_menu.append_item(shared_item)
