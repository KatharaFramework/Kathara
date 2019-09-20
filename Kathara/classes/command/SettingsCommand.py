from consolemenu import *
from consolemenu.items import *
import time

from ..foundation.command.Command import Command
from ..setting.Setting import Setting, DOCKER
from ..validator.ImageValidator import ImageValidator
from consolemenu.format import MenuBorderStyleType
from consolemenu.validators.regex import RegexValidator


class SettingsCommand(Command):
    __slots__ = ['menu']

    def __init__(self):
        Command.__init__(self)

        menu_formatter = MenuFormatBuilder() \
            .set_title_align('center') \
            .set_subtitle_align('center') \
            .set_border_style_type(MenuBorderStyleType.DOUBLE_LINE_BORDER) \
            .show_prologue_top_border(True) \
            .show_prologue_bottom_border(True)

        menu = ConsoleMenu("Kathara Settings", "Choose the option to change", formatter=menu_formatter)

        reset_net_counter_item = FunctionItem("Reset the network counter.", self.resetNetworkCounter)


        select_image_string = "Choose default image."
        select_image_menu = SelectionMenu([],
            title=select_image_string,
            subtitle="Current: %s" % Setting.get_instance().image,
            prologue_text="This is the default image when you launch a lab or a single machine",
            formatter=menu_formatter
            )
        select_image_menu.append_item(FunctionItem("kathara/base", self.choose_image, args=["kathara/base"], should_exit=True))
        select_image_menu.append_item(FunctionItem("kathara/quagga", self.choose_image, args=["kathara/quagga"], should_exit=True))
        select_image_menu.append_item(FunctionItem("kathara/frr", self.choose_image, args=["kathara/frr"], should_exit=True))
        select_image_menu.append_item(FunctionItem("kathara/ovs", self.choose_image, args=["kathara/ovs"], should_exit=True))
        select_image_menu.append_item(FunctionItem("kathara/p4", self.choose_image, args=["kathara/p4"], should_exit=True))
        select_image_menu.append_item(FunctionItem("kathara/netkit_base", self.choose_image, args=["kathara/netkit_base"], should_exit=True))
        select_image_menu.append_item(FunctionItem("Choose another image", self.read_new_image, should_exit=True))

        submenu_item = SubmenuItem(select_image_string, select_image_menu, menu)

        # Manager
        choose_manager_string = "Choose default manager."
        deployer_menu = SelectionMenu([],
            title=choose_manager_string,
            subtitle="Current: %s" % "Kathara (Docker)" if Setting.get_instance().deployer_type == DOCKER else "Megalos (Kubernetes)",
            formatter=menu_formatter,
            prologue_text="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur."
            )

        deployer_menu.append_item(FunctionItem("Kathara (Docker)", self.choose_manager, args=['docker'], should_exit=True))
        deployer_menu.append_item(FunctionItem("Megalos (Kubernetes)", self.choose_manager, args=['k8s'], should_exit=True))

        deployer_item = SubmenuItem(choose_manager_string, deployer_menu, menu)
        # End manager

        # Open Terminals
        open_terminals_string = "Automatically open terminals on startup."
        open_terminals_menu = SelectionMenu([],
            title=open_terminals_string,
            subtitle="Current: %s" % Setting.get_instance().open_terminals,
            formatter=menu_formatter,
            prologue_text="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur."
            )

        open_terminals_menu.append_item(FunctionItem("Yes", self.set_open_terminals, args=[True], should_exit=True))
        open_terminals_menu.append_item(FunctionItem("No", self.set_open_terminals, args=[False], should_exit=True))

        open_terminals_item = SubmenuItem(open_terminals_string, open_terminals_menu, menu)
        # End Open Terminals

        # hosthome
        hosthome_string = "Automatically mount hosthome on startup."
        hosthome_menu = SelectionMenu([],
            title=hosthome_string,
            subtitle="Current: %s" % Setting.get_instance().open_terminals,
            formatter=menu_formatter,
            prologue_text="Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur."
            )

        hosthome_menu.append_item(FunctionItem("Yes", self.set_hosthome, args=[True], should_exit=True))
        hosthome_menu.append_item(FunctionItem("No", self.set_hosthome, args=[False], should_exit=True))

        hosthome_item = SubmenuItem(hosthome_string, hosthome_menu, menu)
        # End hosthome

        # machine_shell
        machine_shell_string = "Choose machine shell to be used."
        machine_shell_menu = SelectionMenu([],
            title=machine_shell_string,
            subtitle="Current: %s" % Setting.get_instance().machine_shell,
            formatter=menu_formatter,
            prologue_text="ATTENZIONE CHE DEVE ESISTERE NELLA IMAGE IMPOSTATA!"
            )

        machine_shell_menu.append_item(FunctionItem("bash", self.set_shell, args=['bash'], should_exit=True))
        machine_shell_menu.append_item(FunctionItem("sh", self.set_shell, args=['sh'], should_exit=True))
        machine_shell_menu.append_item(FunctionItem("ash", self.set_shell, args=['ash'], should_exit=True))
        machine_shell_menu.append_item(FunctionItem("ksh", self.set_shell, args=['ksh'], should_exit=True))
        machine_shell_menu.append_item(FunctionItem("zsh", self.set_shell, args=['zsh'], should_exit=True))
        machine_shell_menu.append_item(FunctionItem("fish", self.set_shell, args=['fish'], should_exit=True))
        machine_shell_menu.append_item(FunctionItem("csh", self.set_shell, args=['csh'], should_exit=True))
        machine_shell_menu.append_item(FunctionItem("tcsh", self.set_shell, args=['tcsh'], should_exit=True))
        machine_shell_menu.append_item(FunctionItem("Choose another shell", self.read_new_shell, should_exit=True))

        machine_shell_item = SubmenuItem(machine_shell_string, machine_shell_menu, menu)
        # End machine_shell

        menu.append_item(reset_net_counter_item)
        menu.append_item(submenu_item)
        menu.append_item(deployer_item)
        menu.append_item(open_terminals_item)
        menu.append_item(hosthome_item)
        menu.append_item(machine_shell_item)

        self.menu = menu

    def run(self, current_path, argv):
        self.menu.show()

    def read_new_shell(self):
        prompt_utils = PromptUtils(Screen())
        #answer = prompt_utils.prompt_for_bilateral_choice('Please enter a value', 'yes', 'no')
        validator = RegexValidator(r"^(\w|/)+$")
        answer = prompt_utils.input(prompt='Write the name of a shell:', validators=validator, enable_quit=True)
        while not answer.validation_result:
            print("Shell name not valid!")
            answer = prompt_utils.input(prompt='Write the name of a shell:', validators=validator, enable_quit=True)
        self.set_shell(answer.input_string)

    def read_new_image(self):
        prompt_utils = PromptUtils(Screen())
        #answer = prompt_utils.prompt_for_bilateral_choice('Please enter a value', 'yes', 'no')
        answer = prompt_utils.input(prompt='Write the name of an image:', validators=ImageValidator(), enable_quit=True)
        time.sleep(2)
        while not answer.validation_result:
            print("Image name not valid!")
            answer = prompt_utils.input(prompt='Write the name of an image:', validators=ImageValidator(), enable_quit=True)

        print("Saved succesfully!")
        time.sleep(2)
        

    def resetNetworkCounter(self):
        Setting.get_instance().net_counter = 0
        # Setting.get_instance().check_net_counter()
        Setting.get_instance().save_selected(['net_counter'])
        print("Saved succesfully!")
        time.sleep(2)

    def choose_manager(self, new_manager):
        Setting.get_instance().deployer_type = new_manager
        Setting.get_instance().check()
        Setting.get_instance().save_selected(['deployer_type'])
        print("Saved succesfully!")
        time.sleep(2)

    def choose_image(self, new_image):
        Setting.get_instance().image = new_image
        Setting.get_instance().check()
        Setting.get_instance().save_selected(['image'])
        print("Saved succesfully!")
        time.sleep(2)

    def set_shell(self, new_shell):
        Setting.get_instance().machine_shell = new_shell
        Setting.get_instance().save_selected(['machine_shell'])
        print("Saved succesfully!")
        time.sleep(2)

    def set_open_terminals(self, new_value):
        Setting.get_instance().open_terminals = bool(new_value)
        Setting.get_instance().save_selected(['open_terminals'])
        print("Saved succesfully!")
        time.sleep(2)

    def set_hosthome(self, new_value):
        Setting.get_instance().hosthome_mount = bool(new_value)
        Setting.get_instance().save_selected(['hosthome_mount'])
        print("Saved succesfully!")
        time.sleep(2)