from ..api.DockerHubApi import DockerHubApi
from ..exceptions import HTTPConnectionError
from ..exceptions import SettingsError
from ..foundation.command.Command import Command
from ..manager.ManagerProxy import ManagerProxy
from ..setting.Setting import Setting, DEFAULTS, POSSIBLE_SHELLS, POSSIBLE_TERMINALS, POSSIBLE_DEBUG_LEVELS
from ..trdparty.consolemenu import *
from ..trdparty.consolemenu.format import MenuBorderStyleType
from ..trdparty.consolemenu.items import *
from ..trdparty.consolemenu.validators.regex import RegexValidator
from ..validator.ImageValidator import ImageValidator
from ..validator.TerminalValidator import TerminalValidator

SAVED_STRING = "Saved successfully!\n"
PRESS_ENTER_STRING = "Press [Enter] to continue."


def format_bool(value):
    return "Yes" if value else "No"


def current_bool(attribute_name, text=None):
    return lambda: "%sCurrent: %s%s" % (text + " (" if text else "",
                                        (format_bool(getattr(Setting.get_instance(), attribute_name))),
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
                           prologue_text="Choose the option to change.",
                           formatter=menu_formatter
                           )

        # Image Selection Submenu
        image_string = "Choose default image"
        select_image_menu = SelectionMenu(strings=[],
                                          title=image_string,
                                          subtitle=current_string("image"),
                                          prologue_text="""Default Docker image when you start a lab or """
                                                        """a single Kathara device.
                                                        Default is `%s`.""" % DEFAULTS['image'],
                                          formatter=menu_formatter
                                          )

        try:
            for image in DockerHubApi.get_images():
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
                                     prologue_text="""Manager in the Engine used to run Kathara machines.
                                                   Default is `%s`.""" % DEFAULTS['manager_type'],
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
                                            prologue_text="""Determines if the device terminal should be opened when starting it.
                                                          Default is %s.""" % format_bool(DEFAULTS['open_terminals']),
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
                                      prologue_text="""The home directory of the current user is made available for """
                                                    """reading/writing inside the device under the special """
                                                    """directory `/hosthome`. 
                                                    Default is %s.""" % format_bool(DEFAULTS['hosthome_mount']),
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
                                    prologue_text="""The shared directory inside the lab folder is made available """
                                                  """for reading/writing inside the device under the special """
                                                  """directory `/shared`.
                                                  
                                                  Default is %s.""" % format_bool(DEFAULTS['shared_mount']),
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
        machine_shell_string = "Choose device shell to be used"
        machine_shell_menu = SelectionMenu(strings=[],
                                           title=machine_shell_string,
                                           subtitle=current_string("device_shell"),
                                           formatter=menu_formatter,
                                           prologue_text="""The shell to use inside the device. 
                                           **The application must be correctly installed in the Docker image used """
                                           """for the device!**
                                           Default is `%s`, but it depends on the used Docker image.
                                           """ % DEFAULTS['device_shell']
                                           )

        for shell in POSSIBLE_SHELLS:
            machine_shell_menu.append_item(FunctionItem(text=shell,
                                                        function=self.set_setting_value,
                                                        args=["device_shell", shell],
                                                        should_exit=True
                                                        )
                                           )
        machine_shell_menu.append_item(FunctionItem(text="Choose another shell",
                                                    function=self.read_value,
                                                    args=['device_shell',
                                                          RegexValidator(r"^(\w|/)+$"),
                                                          'Write the name of a shell:',
                                                          'Shell name is not valid!'
                                                          ],
                                                    should_exit=True
                                                    )
                                       )

        machine_shell_item = SubmenuItem(machine_shell_string, machine_shell_menu, menu)

        # Terminal Emulator Submenu
        terminal_string = "Choose terminal emulator to be used"
        terminal_menu = SelectionMenu(strings=[],
                                      title=terminal_string,
                                      subtitle=current_string("terminal"),
                                      formatter=menu_formatter,
                                      prologue_text="""The terminal emulator application to be used for device terminals.
                                                    **The application must be correctly installed in the host system!**
                                                    This setting is only used on Linux systems.
                                                    Default is `%s`.
                                                    """ % DEFAULTS['terminal']
                                      )

        for terminal in POSSIBLE_TERMINALS:
            terminal_menu.append_item(FunctionItem(text=terminal,
                                                   function=self.set_setting_value,
                                                   args=["terminal", terminal],
                                                   should_exit=True
                                                   )
                                      )
        terminal_menu.append_item(FunctionItem(text="Choose another terminal emulator",
                                               function=self.read_value,
                                               args=['terminal',
                                                     TerminalValidator(),
                                                     'Write the name of a terminal emulator:',
                                                     'Terminal emulator is not valid!'
                                                     ],
                                               should_exit=True
                                               )
                                  )

        terminal_item = SubmenuItem(terminal_string, terminal_menu, menu)

        # Prefixes Submenu
        prefixes_string = "Choose Kathara prefixes"
        prefixes_menu = SelectionMenu(strings=[],
                                      title=prefixes_string,
                                      formatter=menu_formatter,
                                      prologue_text="""Prefixes assigned to the network and device names when deployed.
                                                    Default is `%s` and `%s`.""" % (DEFAULTS['net_prefix'],
                                                                                    DEFAULTS['device_prefix'])
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

        machine_prefix_item = FunctionItem(text=current_string("device_prefix", text="Insert Kathara devices prefix"),
                                           function=self.read_value,
                                           args=['device_prefix',
                                                 RegexValidator(r"^[a-z]+_?[a-z_]+$"),
                                                 'Write a Kathara devices prefix:',
                                                 'Device Prefix must only contain lowercase letters and underscore.'
                                                 ],
                                           should_exit=True
                                           )
        prefixes_menu.append_item(machine_prefix_item)

        prefixes_item = SubmenuItem(prefixes_string, prefixes_menu, menu)

        # Debug Level Submenu
        debug_level_string = "Choose logging level to be used"
        debug_level_menu = SelectionMenu(strings=[],
                                         title=debug_level_string,
                                         subtitle=current_string("debug_level"),
                                         formatter=menu_formatter,
                                         prologue_text="""Logging level of Kathara messages.
                                                       Default is `%s`.""" % DEFAULTS['debug_level']
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
        print_startup_log_string = "Print Startup Logs on device startup"
        print_startup_log_menu = SelectionMenu(strings=[],
                                               title=open_terminals_string,
                                               subtitle=current_bool("print_startup_log"),
                                               formatter=menu_formatter,
                                               prologue_text="""When opening a device terminal, print its startup log.
                                                             Default is %s.""" % format_bool(
                                                                                          DEFAULTS['print_startup_log'])
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


        # Enable ipv6 Option
        enable_ipv6_string = "Enable IPv6"
        enable_ipv6_menu = SelectionMenu(strings=[],
                                         title=enable_ipv6_string,
                                         subtitle=current_bool("enable_ipv6"),
                                         formatter=menu_formatter,
                                         prologue_text="""This option enables IPv6 inside the devices.
                                                          Default is %s.""" % format_bool(
                                                          DEFAULTS['enable_ipv6'])
                                        )

        enable_ipv6_menu.append_item(FunctionItem(text="Yes",
                                                  function=self.set_setting_value,
                                                  args=['enable_ipv6', True],
                                                  should_exit=True
                                                  )
                                     )
        enable_ipv6_menu.append_item(FunctionItem(text="No",
                                                  function=self.set_setting_value,
                                                  args=['enable_ipv6', False],
                                                  should_exit=True
                                                  )
                                    )

        enable_ipv6_item = SubmenuItem(enable_ipv6_string, enable_ipv6_menu, menu)

        menu.append_item(submenu_item)
        menu.append_item(manager_item)
        menu.append_item(open_terminals_item)
        menu.append_item(hosthome_item)
        menu.append_item(shared_item)
        menu.append_item(machine_shell_item)
        menu.append_item(terminal_item)
        menu.append_item(prefixes_item)
        menu.append_item(debug_level_item)
        menu.append_item(print_startup_log_item)
        menu.append_item(enable_ipv6_item)

        self.menu = menu

    def run(self, current_path, argv):
        self.menu.show()

    @staticmethod
    def set_setting_value(attribute_name, value):
        setattr(Setting.get_instance(), attribute_name, value)
        try:
            Setting.get_instance().check()

            Setting.get_instance().save_selected([attribute_name])

            print(SAVED_STRING)
        except SettingsError as e:
            print(str(e))

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
