from ..api.DockerHubApi import DockerHubApi
from ..exceptions import HTTPConnectionError
from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy
from ..setting.Setting import Setting, POSSIBLE_SHELLS, POSSIBLE_DEBUG_LEVELS, EXCLUDED_IMAGES
from ..trdparty.consolemenu import *
from ..trdparty.consolemenu.format import MenuBorderStyleType
from ..trdparty.consolemenu.items import *
from ..trdparty.consolemenu.validators.regex import RegexValidator
from ..validator.ImageValidator import ImageValidator

SAVED_STRING = "Saved successfully!\n"
PRESS_ENTER_STRING = "Press [Enter] to continue."


def current_bool(attribute_name, text=None):
    return lambda: "%sCurrent: %s%s" % (text + " (" if text else "",
                                        ("Yes" if getattr(Setting.get_instance(), attribute_name) else "No"),
                                        ")" if text else ""
                                        )


def current_string(attribute_name, text=None):
    return lambda: "%sCurrent: %s%s" % (text + " (" if text else "",
                                        getattr(Setting.get_instance(), attribute_name),
                                        ")" if text else ""
                                        )


class SettingsCommand(Command):
    __slots__ = ['menu']

    def __init__(self):
        Command.__init__(self)

        menu_formatter = MenuFormatBuilder().set_title_align('center') \
                                            .set_subtitle_align('center') \
                                            .set_prologue_text_align('center') \
                                            .set_border_style_type(MenuBorderStyleType.DOUBLE_LINE_BORDER) \
                                            .show_prologue_top_border(True) \
                                            .show_prologue_bottom_border(True)

        # Main Menu
        menu = ConsoleMenu(title="Kathara Settings",
                           prologue_text="Choose the option to change",
                           formatter=menu_formatter
                           )

        # Image Selection Submenu
        image_string = "Choose default image"
        select_image_menu = SelectionMenu(strings=[],
                                          title=image_string,
                                          subtitle=current_string("image"),
                                          prologue_text="Default Docker image when you start a lab or a single machine",
                                          formatter=menu_formatter
                                          )

        try:
            for image in DockerHubApi.get_images():
                if image['name'] in EXCLUDED_IMAGES:
                    continue

                image_name = "%s/%s" % (image['namespace'], image['name'])

                select_image_menu.append_item(FunctionItem(text=image_name,
                                                           function=self.set_setting_value,
                                                           args=['image', image_name],
                                                           should_exit=True
                                                           )
                                              )
        except HTTPConnectionError:
            pass

        select_image_menu.append_item(FunctionItem(text="Choose another image",
                                                   function=self.read_value,
                                                   args=['image',
                                                         ImageValidator(),
                                                         'Write the name of a Docker image available on Docker Hub:',
                                                         'Docker Image not available neither on Docker Hub nor '
                                                         'in local repository!'
                                                         ],
                                                   should_exit=True
                                                   )
                                      )
        submenu_item = SubmenuItem(image_string, select_image_menu, menu)

        # Manager Submenu
        managers = ManagerProxy.get_available_managers_name()
        manager_type = Setting.get_instance().manager_type

        choose_manager_string = "Choose default manager"
        manager_menu = SelectionMenu(strings=[],
                                     title=choose_manager_string,
                                     subtitle=lambda: "Current: %s" % managers[manager_type],
                                     formatter=menu_formatter
                                     )

        for (name, formatted_name) in managers.items():
            manager_menu.append_item(FunctionItem(text=formatted_name,
                                                  function=self.set_setting_value,
                                                  args=['manager_type', name],
                                                  should_exit=True
                                                  )
                                     )

        manager_item = SubmenuItem(choose_manager_string, manager_menu, menu)

        # Open Terminals Option
        open_terminals_string = "Automatically open terminals on startup"
        open_terminals_menu = SelectionMenu(strings=[],
                                            title=open_terminals_string,
                                            subtitle=current_bool("open_terminals"),
                                            formatter=menu_formatter
                                            )

        open_terminals_menu.append_item(FunctionItem(text="Yes",
                                                     function=self.set_setting_value,
                                                     args=['open_terminals', True],
                                                     should_exit=True
                                                     )
                                        )
        open_terminals_menu.append_item(FunctionItem(text="No",
                                                     function=self.set_setting_value,
                                                     args=['open_terminals', False],
                                                     should_exit=True
                                                     )
                                        )

        open_terminals_item = SubmenuItem(open_terminals_string, open_terminals_menu, menu)

        # Hosthome Mount Option
        hosthome_string = "Automatically mount /hosthome on startup"
        hosthome_menu = SelectionMenu(strings=[],
                                      title=hosthome_string,
                                      subtitle=current_bool("hosthome_mount"),
                                      formatter=menu_formatter
                                      )

        hosthome_menu.append_item(FunctionItem(text="Yes",
                                               function=self.set_setting_value,
                                               args=["hosthome_mount", True],
                                               should_exit=True
                                               )
                                  )
        hosthome_menu.append_item(FunctionItem(text="No",
                                               function=self.set_setting_value,
                                               args=["hosthome_mount", False],
                                               should_exit=True
                                               )
                                  )

        hosthome_item = SubmenuItem(hosthome_string, hosthome_menu, menu)

        # Shared Mount Option
        shared_string = "Automatically mount /shared on startup"
        shared_menu = SelectionMenu(strings=[],
                                    title=shared_string,
                                    subtitle=current_bool("shared_mount"),
                                    formatter=menu_formatter
                                    )

        shared_menu.append_item(FunctionItem(text="Yes",
                                             function=self.set_setting_value,
                                             args=["shared_mount", True],
                                             should_exit=True
                                             )
                                )
        shared_menu.append_item(FunctionItem(text="No",
                                             function=self.set_setting_value,
                                             args=["shared_mount", False],
                                             should_exit=True
                                             )
                                )

        shared_item = SubmenuItem(shared_string, shared_menu, menu)

        # Machine Shell Submenu
        machine_shell_string = "Choose machine shell to be used"
        machine_shell_menu = SelectionMenu(strings=[],
                                           title=machine_shell_string,
                                           subtitle=current_string("machine_shell"),
                                           formatter=menu_formatter,
                                           prologue_text="ATTENZIONE CHE DEVE ESISTERE NELLA IMAGE IMPOSTATA!"
                                           )

        for shell in POSSIBLE_SHELLS:
            machine_shell_menu.append_item(FunctionItem(text=shell,
                                                        function=self.set_setting_value,
                                                        args=["machine_shell", shell],
                                                        should_exit=True
                                                        )
                                           )
        machine_shell_menu.append_item(FunctionItem(text="Choose another shell",
                                                    function=self.read_value,
                                                    args=['machine_shell',
                                                          RegexValidator(r"^(\w|/)+$"),
                                                          'Write the name of a shell:',
                                                          'Shell name is not valid!'
                                                          ],
                                                    should_exit=True
                                                    )
                                       )

        machine_shell_item = SubmenuItem(machine_shell_string, machine_shell_menu, menu)

        # Prefixes Submenu
        prefixes_string = "Choose Kathara prefixes"
        prefixes_menu = SelectionMenu(strings=[],
                                      title=prefixes_string,
                                      formatter=menu_formatter,
                                      prologue_text="Text Here"
                                      )

        net_prefix_item = FunctionItem(text=current_string("net_prefix", text="Insert Kathara networks prefix"),
                                       function=self.read_value,
                                       args=['net_prefix',
                                             RegexValidator(r"^[a-z]+_?[a-z_]+$"),
                                             'Write a Kathara networks prefix:',
                                             'Network Prefix must only contain lowercase letters and underscore.'
                                             ],
                                       should_exit=True
                                       )
        prefixes_menu.append_item(net_prefix_item)

        machine_prefix_item = FunctionItem(text=current_string("machine_prefix", text="Insert Kathara machines prefix"),
                                           function=self.read_value,
                                           args=['machine_prefix',
                                                 RegexValidator(r"^[a-z]+_?[a-z_]+$"),
                                                 'Write a Kathara machines prefix:',
                                                 'Machine Prefix must only contain lowercase letters and underscore.'
                                                 ],
                                           should_exit=True
                                           )
        prefixes_menu.append_item(machine_prefix_item)

        prefixes_item = SubmenuItem(prefixes_string, prefixes_menu, menu)

        # Debug Level Submenu
        debug_level_string = "Choose debug level to be used"
        debug_level_menu = SelectionMenu(strings=[],
                                         title=debug_level_string,
                                         subtitle=current_string("debug_level"),
                                         formatter=menu_formatter,
                                         prologue_text="Text here"
                                         )

        for debug_level in POSSIBLE_DEBUG_LEVELS:
            debug_level_menu.append_item(FunctionItem(text=debug_level,
                                                      function=self.set_setting_value,
                                                      args=["debug_level", debug_level],
                                                      should_exit=True
                                                      )
                                         )

        debug_level_item = SubmenuItem(debug_level_string, debug_level_menu, menu)

        # Print Startup Logs Option
        print_startup_log_string = "Print Startup Logs on machine startup"
        print_startup_log_menu = SelectionMenu(strings=[],
                                               title=open_terminals_string,
                                               subtitle=current_bool("print_startup_log"),
                                               formatter=menu_formatter
                                               )

        print_startup_log_menu.append_item(FunctionItem(text="Yes",
                                                        function=self.set_setting_value,
                                                        args=['print_startup_log', True],
                                                        should_exit=True
                                                        )
                                           )
        print_startup_log_menu.append_item(FunctionItem(text="No",
                                                        function=self.set_setting_value,
                                                        args=['print_startup_log', False],
                                                        should_exit=True
                                                        )
                                           )

        print_startup_log_item = SubmenuItem(print_startup_log_string, print_startup_log_menu, menu)

        menu.append_item(submenu_item)
        menu.append_item(manager_item)
        menu.append_item(open_terminals_item)
        menu.append_item(hosthome_item)
        menu.append_item(shared_item)
        menu.append_item(machine_shell_item)
        menu.append_item(prefixes_item)
        menu.append_item(debug_level_item)
        menu.append_item(print_startup_log_item)

        self.menu = menu

    def run(self, current_path, argv):
        self.menu.show()

    @staticmethod
    def set_setting_value(attribute_name, value):
        setattr(Setting.get_instance(), attribute_name, value)
        Setting.get_instance().check()
        Setting.get_instance().save_selected([attribute_name])

        print(SAVED_STRING)

        Screen().input(PRESS_ENTER_STRING)

    @staticmethod
    def _read_and_validate_value(prompt_msg, validator):
        prompt_utils = PromptUtils(Screen())
        answer = prompt_utils.input(prompt=prompt_msg,
                                    validators=validator,
                                    enable_quit=True
                                    )

        return answer

    @staticmethod
    def read_value(attribute_name, validator, prompt_msg, error_msg):
        answer = SettingsCommand._read_and_validate_value(prompt_msg=prompt_msg,
                                                          validator=validator
                                                          )

        while not answer.validation_result:
            print(error_msg)
            answer = SettingsCommand._read_and_validate_value(prompt_msg=prompt_msg,
                                                              validator=validator
                                                              )

        setattr(Setting.get_instance(), attribute_name, answer.input_string)
        Setting.get_instance().save_selected([attribute_name])

        print(SAVED_STRING)

        Screen().input(PRESS_ENTER_STRING)
