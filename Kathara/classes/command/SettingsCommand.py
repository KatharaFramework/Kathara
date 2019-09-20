from consolemenu import *
from consolemenu.items import *
import time

from ..foundation.command.Command import Command
from ..setting.Setting import Setting


class SettingsCommand(Command):
    __slots__ = ['menu']

    def __init__(self):
        Command.__init__(self)

        menu = ConsoleMenu("Kathara Settings", "Choose the option to change")

        reset_net_counter_item = FunctionItem("Reset the network counter", self.resetNetworkCounter)


        select_image_string = "Choose default image"
        select_image_menu = SelectionMenu([], title=select_image_string)
        select_image_menu.append_item(FunctionItem("kathara/base", self.choose_image, args=["kathara/base"], should_exit=True))
        select_image_menu.append_item(FunctionItem("kathara/quagga", self.choose_image, args=["kathara/quagga"], should_exit=True))
        select_image_menu.append_item(FunctionItem("kathara/frr", self.choose_image, args=["kathara/frr"], should_exit=True))
        select_image_menu.append_item(FunctionItem("kathara/ovs", self.choose_image, args=["kathara/ovs"], should_exit=True))
        select_image_menu.append_item(FunctionItem("kathara/p4", self.choose_image, args=["kathara/p4"], should_exit=True))
        select_image_menu.append_item(FunctionItem("kathara/netkit_base", self.choose_image, args=["kathara/netkit_base"], should_exit=True))
        select_image_menu.append_item(FunctionItem("Choose another image", self.read_new_image, should_exit=True))

        submenu_item = SubmenuItem(select_image_string, select_image_menu, menu)

        # Manager
        choose_manager_string = "Choose default manager"
        deployer_menu = SelectionMenu([], title=choose_manager_string)

        deployer_menu.append_item(FunctionItem("Kathara (Docker)", self.choose_manager, args=['docker'], should_exit=True))
        deployer_menu.append_item(FunctionItem("Megalos (Kubernetes)", self.choose_manager, args=['k8s'], should_exit=True))

        deployer_item = SubmenuItem(choose_manager_string, deployer_menu, menu)
        # End manager

        menu.append_item(reset_net_counter_item)
        menu.append_item(submenu_item)
        menu.append_item(deployer_item)

        self.menu = menu

    def run(self, current_path, argv):
        self.menu.show()

    def read_new_image(self):
        prompt_utils = PromptUtils(Screen())
        #answer = prompt_utils.prompt_for_bilateral_choice('Please enter a value', 'yes', 'no')
        answer = prompt_utils.input(prompt='Write the name of an image:', enable_quit=False)
        print(answer.input_string)
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