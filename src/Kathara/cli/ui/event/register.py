from .HandleMachineTerminal import HandleMachineTerminal
from .HandleProgressBar import HandleProgressBar
from .UpdateDockerImage import UpdateDockerImage
from ....event.EventDispatcher import EventDispatcher


def register_cli_events() -> None:
    """Register events to handle UI from CLI.

    Returns:
        None
    """
    _register_link_events()
    _register_machine_events()

    EventDispatcher.get_instance().register("docker_image_update_found", UpdateDockerImage())


def _register_link_events() -> None:
    link_deploy_progress_bar_handler = HandleProgressBar('Deploying collision domains...')
    EventDispatcher.get_instance().register("links_deploy_started", link_deploy_progress_bar_handler, "init")
    EventDispatcher.get_instance().register("link_deployed", link_deploy_progress_bar_handler, "update")
    EventDispatcher.get_instance().register("links_deploy_ended", link_deploy_progress_bar_handler, "finish")

    link_undeploy_progress_bar_handler = HandleProgressBar('Deleting collision domains...')
    EventDispatcher.get_instance().register("links_undeploy_started", link_undeploy_progress_bar_handler, "init")
    EventDispatcher.get_instance().register("link_undeployed", link_undeploy_progress_bar_handler, "update")
    EventDispatcher.get_instance().register("links_undeploy_ended", link_undeploy_progress_bar_handler, "finish")


def _register_machine_events() -> None:
    machine_deploy_progress_bar_handler = HandleProgressBar('Deploying devices...')
    EventDispatcher.get_instance().register("machines_deploy_started", machine_deploy_progress_bar_handler, "init")
    EventDispatcher.get_instance().register("machine_deployed", machine_deploy_progress_bar_handler, "update")
    EventDispatcher.get_instance().register("machines_deploy_ended", machine_deploy_progress_bar_handler, "finish")

    machine_undeploy_progress_bar_handler = HandleProgressBar('Deleting devices...')
    EventDispatcher.get_instance().register("machines_undeploy_started", machine_undeploy_progress_bar_handler, "init")
    EventDispatcher.get_instance().register("machine_undeployed", machine_undeploy_progress_bar_handler, "update")
    EventDispatcher.get_instance().register("machines_undeploy_ended", machine_undeploy_progress_bar_handler, "finish")

    machine_terminal_handler = HandleMachineTerminal()
    EventDispatcher.get_instance().register("machine_deployed", machine_terminal_handler, "run")
    EventDispatcher.get_instance().register("machine_startup_wait_started", machine_terminal_handler, "print_wait_msg")
    EventDispatcher.get_instance().register("machine_startup_wait_ended", machine_terminal_handler, "flush")
