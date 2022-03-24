from .UpdateDockerImage import UpdateDockerImage
from .OpenMachineTerminal import OpenMachineTerminal
from .HandleProgressBar import ProgressBarHandler
from ....event.EventDispatcher import EventDispatcher


def register_cli_events() -> None:
    """
    Register events to handle UI from CLI.

    Returns:
        None
    """
    _register_link_events()
    _register_machine_events()

    EventDispatcher.get_instance().register("docker_image_update_found", UpdateDockerImage())


def _register_link_events() -> None:
    link_deploy_progress_bar_handler = ProgressBarHandler('Deploying collision domains...')
    EventDispatcher.get_instance().register("links_deploy_started", link_deploy_progress_bar_handler, "init")
    EventDispatcher.get_instance().register("link_deployed", link_deploy_progress_bar_handler, "update")
    EventDispatcher.get_instance().register("links_deploy_ended", link_deploy_progress_bar_handler, "finish")

    link_undeploy_progress_bar_handler = ProgressBarHandler('Deleting collision domains...')
    EventDispatcher.get_instance().register("links_undeploy_started", link_undeploy_progress_bar_handler, "init")
    EventDispatcher.get_instance().register("link_undeployed", link_undeploy_progress_bar_handler, "update")
    EventDispatcher.get_instance().register("links_undeploy_ended", link_undeploy_progress_bar_handler, "finish")


def _register_machine_events() -> None:
    machine_deploy_progress_bar_handler = ProgressBarHandler('Deploying devices...')
    EventDispatcher.get_instance().register("machines_deploy_started", machine_deploy_progress_bar_handler, "init")
    EventDispatcher.get_instance().register("machine_deployed", machine_deploy_progress_bar_handler, "update")
    EventDispatcher.get_instance().register("machines_deploy_ended", machine_deploy_progress_bar_handler, "finish")

    machine_undeploy_progress_bar_handler = ProgressBarHandler('Deleting devices...')
    EventDispatcher.get_instance().register("machines_undeploy_started", machine_undeploy_progress_bar_handler, "init")
    EventDispatcher.get_instance().register("machine_undeployed", machine_undeploy_progress_bar_handler, "update")
    EventDispatcher.get_instance().register("machines_undeploy_ended", machine_undeploy_progress_bar_handler, "finish")

    EventDispatcher.get_instance().register("machine_deployed", OpenMachineTerminal())
