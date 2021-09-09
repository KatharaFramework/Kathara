from . import utils as setting_utils
from ....connectors.DockerHubApi import DockerHubApi
from ....exceptions import HTTPConnectionError
from ....foundation.cli.ui.setting.OptionsHandler import OptionsHandler
from ....manager.Kathara import Kathara
from ....setting.Setting import Setting, DEFAULTS, AVAILABLE_DEBUG_LEVELS
from ....trdparty.consolemenu import *
from ....trdparty.consolemenu.items import *
from ....trdparty.consolemenu.validators.regex import RegexValidator
from ....utils import exec_by_platform
from ....validator.ImageValidator import ImageValidator
from ....validator.TerminalValidator import TerminalValidator

SHELLS_HINT = ["/bin/bash", "/bin/sh", "/bin/ash", "/bin/ksh", "/bin/zsh", "/bin/fish", "/bin/csh", "/bin/tcsh"]
TERMINALS_OSX = ["Terminal", "iTerm"]


class CommonOptionsHandler(OptionsHandler):
    def add_items(self, current_menu: ConsoleMenu, menu_formatter: MenuFormatBuilder) -> None:
        # Manager Submenu
        managers = Kathara.get_available_managers_name()
        manager_type = Setting.get_instance().manager_type

        choose_manager_string = "Choose default manager"
        manager_menu = SelectionMenu(strings=[],
                                     title=choose_manager_string,
                                     subtitle=lambda: "Current: %s" % managers[manager_type],
                                     prologue_text="""Manager is the Engine used to run Kathara labs.
                                                   Default is `%s`.""" % managers[DEFAULTS['manager_type']],
                                     formatter=menu_formatter
                                     )

        for name, formatted_name in managers.items():
            manager_menu.append_item(FunctionItem(text=formatted_name,
                                                  function=self.update_manager_value,
                                                  args=[current_menu, name],
                                                  should_exit=True
                                                  )
                                     )

        manager_item = SubmenuItem(choose_manager_string, manager_menu, current_menu)

        # Image Selection Submenu
        image_string = "Choose default image"
        select_image_menu = SelectionMenu(strings=[],
                                          title=image_string,
                                          subtitle=setting_utils.current_string("image"),
                                          prologue_text="""Default Docker image when you start a lab or """
                                                        """a single Kathara device.
                                                        Default is `%s`.""" % DEFAULTS['image'],
                                          formatter=menu_formatter
                                          )

        try:
            for image in DockerHubApi.get_images():
                image_name = "%s/%s" % (image['namespace'], image['name'])

                select_image_menu.append_item(FunctionItem(text=image_name,
                                                           function=setting_utils.update_setting_value,
                                                           args=['image', image_name],
                                                           should_exit=True
                                                           )
                                              )
        except HTTPConnectionError:
            pass

        select_image_menu.append_item(FunctionItem(text="Choose another image",
                                                   function=setting_utils.read_value,
                                                   args=['image',
                                                         ImageValidator(),
                                                         'Write the name of a Docker image available on Docker Hub:',
                                                         'Docker Image not available neither on Docker Hub nor '
                                                         'in local repository!'
                                                         ],
                                                   should_exit=True
                                                   )
                                      )
        submenu_item = SubmenuItem(image_string, select_image_menu, current_menu)

        # Open Terminals Option
        open_terminals_string = "Automatically open terminals on startup"
        open_terminals_menu = SelectionMenu(strings=[],
                                            title=open_terminals_string,
                                            subtitle=setting_utils.current_bool("open_terminals"),
                                            prologue_text="""Determines if the device terminal should be opened """
                                                          """when starting it.
                                                          Default is %s."""
                                                          % setting_utils.format_bool(DEFAULTS['open_terminals']),
                                            formatter=menu_formatter
                                            )

        open_terminals_menu.append_item(FunctionItem(text="Yes",
                                                     function=setting_utils.update_setting_value,
                                                     args=['open_terminals', True],
                                                     should_exit=True
                                                     )
                                        )
        open_terminals_menu.append_item(FunctionItem(text="No",
                                                     function=setting_utils.update_setting_value,
                                                     args=['open_terminals', False],
                                                     should_exit=True
                                                     )
                                        )

        open_terminals_item = SubmenuItem(open_terminals_string, open_terminals_menu, current_menu)

        # Machine Shell Submenu
        machine_shell_string = "Choose device shell to be used"
        machine_shell_menu = SelectionMenu(strings=[],
                                           title=machine_shell_string,
                                           subtitle=setting_utils.current_string("device_shell"),
                                           formatter=menu_formatter,
                                           prologue_text="""The shell to use inside the device. 
                                                         **The application must be correctly installed in the Docker 
                                                         image used for the device!**
                                                         Default is `%s`, but it depends on the used Docker image.
                                                         """ % DEFAULTS['device_shell']
                                           )

        for shell in SHELLS_HINT:
            machine_shell_menu.append_item(FunctionItem(text=shell,
                                                        function=setting_utils.update_setting_value,
                                                        args=["device_shell", shell],
                                                        should_exit=True
                                                        )
                                           )
        machine_shell_menu.append_item(FunctionItem(text="Choose another shell",
                                                    function=setting_utils.read_value,
                                                    args=['device_shell',
                                                          RegexValidator(r"^(\w|/)+$"),
                                                          'Write the name of a shell:',
                                                          'Shell name is not valid!'
                                                          ],
                                                    should_exit=True
                                                    )
                                       )

        machine_shell_item = SubmenuItem(machine_shell_string, machine_shell_menu, current_menu)

        # Terminal Emulator Submenu
        # Linux Version
        def terminal_emulator_menu_linux():
            terminal_string = "Choose terminal emulator to be used"
            terminal_menu = SelectionMenu(strings=[],
                                          title=terminal_string,
                                          subtitle=setting_utils.current_string("terminal"),
                                          formatter=menu_formatter,
                                          prologue_text="""Terminal emulator application to be used for device """
                                                        """terminals. 
                                                        **The application must be correctly installed in """
                                                        """the host system!**
                                                        Default is `%s`.""" % DEFAULTS['terminal']
                                          )

            terminal_menu.append_item(FunctionItem(text="/usr/bin/xterm",
                                                   function=setting_utils.update_setting_value,
                                                   args=["terminal", "/usr/bin/xterm"],
                                                   should_exit=True
                                                   )
                                      )
            terminal_menu.append_item(FunctionItem(text="TMUX",
                                                   function=setting_utils.update_setting_value,
                                                   args=["terminal", "TMUX"],
                                                   should_exit=True
                                                   )
                                      )
            terminal_menu.append_item(FunctionItem(text="Choose another terminal emulator",
                                                   function=setting_utils.read_value,
                                                   args=['terminal',
                                                         TerminalValidator(),
                                                         'Write the path of a terminal emulator:',
                                                         'Terminal emulator is not valid! Install it before using it.'
                                                         ],
                                                   should_exit=True
                                                   )
                                      )

            return SubmenuItem(terminal_string, terminal_menu, current_menu)

        # macOS Version
        def terminal_emulator_menu_osx():
            terminal_string = "Choose terminal emulator to be used"
            terminal_menu = SelectionMenu(strings=[],
                                          title=terminal_string,
                                          subtitle=setting_utils.current_string("terminal"),
                                          formatter=menu_formatter,
                                          prologue_text="""Terminal emulator application to be used for device """
                                                        """terminals. 
                                                        **The application must be correctly installed in """
                                                        """the host system!**
                                                        Default is `Terminal`."""
                                          )

            for terminal in TERMINALS_OSX:
                terminal_menu.append_item(FunctionItem(text=terminal,
                                                       function=setting_utils.update_setting_value,
                                                       args=["terminal", terminal],
                                                       should_exit=True
                                                       )
                                          )
            terminal_menu.append_item(FunctionItem(text="TMUX",
                                                   function=setting_utils.update_setting_value,
                                                   args=["terminal", "TMUX"],
                                                   should_exit=True
                                                   )
                                      )

            return SubmenuItem(terminal_string, terminal_menu, current_menu)

        terminal_item = exec_by_platform(terminal_emulator_menu_linux, lambda: None, terminal_emulator_menu_osx)

        # Prefixes Submenu
        prefixes_string = "Choose Kathara prefixes"
        prefixes_menu = SelectionMenu(strings=[],
                                      title=prefixes_string,
                                      formatter=menu_formatter,
                                      prologue_text="""Prefixes assigned to the network and device names when deployed.
                                                    Default is `%s` and `%s`.""" % (DEFAULTS['net_prefix'],
                                                                                    DEFAULTS['device_prefix'])
                                      )

        net_prefix_item = FunctionItem(text=setting_utils.current_string("net_prefix",
                                                                         text="Insert Kathara networks prefix"),
                                       function=setting_utils.read_value,
                                       args=['net_prefix',
                                             RegexValidator(r"^[a-z]+_?[a-z_]+$"),
                                             'Write a Kathara networks prefix:',
                                             'Network Prefix must only contain lowercase letters and underscore.'
                                             ],
                                       should_exit=True
                                       )
        prefixes_menu.append_item(net_prefix_item)

        machine_prefix_item = FunctionItem(text=setting_utils.current_string("device_prefix",
                                                                             text="Insert Kathara devices prefix"),
                                           function=setting_utils.read_value,
                                           args=['device_prefix',
                                                 RegexValidator(r"^[a-z]+_?[a-z_]+$"),
                                                 'Write a Kathara devices prefix:',
                                                 'Device Prefix must only contain lowercase letters and underscore.'
                                                 ],
                                           should_exit=True
                                           )
        prefixes_menu.append_item(machine_prefix_item)

        prefixes_item = SubmenuItem(prefixes_string, prefixes_menu, current_menu)

        # Debug Level Submenu
        debug_level_string = "Choose logging level to be used"
        debug_level_menu = SelectionMenu(strings=[],
                                         title=debug_level_string,
                                         subtitle=setting_utils.current_string("debug_level"),
                                         formatter=menu_formatter,
                                         prologue_text="""Logging level of Kathara messages.
                                                       Default is `%s`.""" % DEFAULTS['debug_level']
                                         )

        for debug_level in AVAILABLE_DEBUG_LEVELS:
            debug_level_menu.append_item(FunctionItem(text=debug_level,
                                                      function=setting_utils.update_setting_value,
                                                      args=["debug_level", debug_level],
                                                      should_exit=True
                                                      )
                                         )

        debug_level_item = SubmenuItem(debug_level_string, debug_level_menu, current_menu)

        # Print Startup Logs Option
        print_startup_log_string = "Print Startup Logs on device startup"
        print_startup_log_menu = SelectionMenu(strings=[],
                                               title=open_terminals_string,
                                               subtitle=setting_utils.current_bool("print_startup_log"),
                                               formatter=menu_formatter,
                                               prologue_text="""When opening a device terminal, print its startup log.
                                                             Default is %s.""" %
                                                             setting_utils.format_bool(DEFAULTS['print_startup_log'])
                                               )

        print_startup_log_menu.append_item(FunctionItem(text="Yes",
                                                        function=setting_utils.update_setting_value,
                                                        args=['print_startup_log', True],
                                                        should_exit=True
                                                        )
                                           )
        print_startup_log_menu.append_item(FunctionItem(text="No",
                                                        function=setting_utils.update_setting_value,
                                                        args=['print_startup_log', False],
                                                        should_exit=True
                                                        )
                                           )

        print_startup_log_item = SubmenuItem(print_startup_log_string, print_startup_log_menu, current_menu)

        # Enable IPv6 Option
        enable_ipv6_string = "Enable IPv6"
        enable_ipv6_menu = SelectionMenu(strings=[],
                                         title=enable_ipv6_string,
                                         subtitle=setting_utils.current_bool("enable_ipv6"),
                                         formatter=menu_formatter,
                                         prologue_text="""This option enables IPv6 inside the devices.
                                                       Default is %s.""" %
                                                       setting_utils.format_bool(DEFAULTS['enable_ipv6']))

        enable_ipv6_menu.append_item(FunctionItem(text="Yes",
                                                  function=setting_utils.update_setting_value,
                                                  args=['enable_ipv6', True],
                                                  should_exit=True
                                                  )
                                     )
        enable_ipv6_menu.append_item(FunctionItem(text="No",
                                                  function=setting_utils.update_setting_value,
                                                  args=['enable_ipv6', False],
                                                  should_exit=True
                                                  )
                                     )

        enable_ipv6_item = SubmenuItem(enable_ipv6_string, enable_ipv6_menu, current_menu)

        current_menu.append_item(manager_item)
        current_menu.append_item(submenu_item)
        current_menu.append_item(open_terminals_item)
        current_menu.append_item(machine_shell_item)
        if terminal_item:
            current_menu.append_item(terminal_item)
        current_menu.append_item(prefixes_item)
        current_menu.append_item(debug_level_item)
        current_menu.append_item(print_startup_log_item)
        current_menu.append_item(enable_ipv6_item)

    def update_manager_value(self, current_menu: ConsoleMenu, value: str) -> None:
        setting_utils.update_setting_value("manager_type", value)

        # exit() does not work. So we force the menu to exit as the user selected the Exit option.
        # This is always the last item of the current menu.
        exit_option = len(current_menu.items) - 1
        current_menu.go_to(exit_option)

        clear_terminal()

        # Create a new menu (Manager could be changed so specific options need to be changed)
        new_menu = self.menu_factory.create_menu()
        new_menu.draw()
        new_menu.show()
