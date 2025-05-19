from rich.console import Console
from rich.table import Table

strings = {
    "vstart": "Start a new Kathara device",
    "vclean": "Stop a single Kathara device",
    "vconfig": "Manage the network interfaces of a running Kathara device",
    "lstart": "Start a Kathara network scenario",
    "lclean": "Stop a Kathara network scenario",
    "linfo": "Show information about a Kathara network scenario",
    "lrestart": "Restart a Kathara network scenario",
    "lconfig": "Manage the network interfaces of a running Kathara device in a Kathara network scenario",
    "connect": "Connect to a Kathara device",
    "exec": "Execute a command in a Kathara device",
    "wipe": "Delete all Kathara devices and collision domains, optionally also delete settings",
    "list": "Show all running Kathara devices of the current user",
    "settings": "Show and edit Kathara settings",
    "check": "Check your system environment"
}

wiki_description = "For examples and further information visit: https://github.com/KatharaFramework/Kathara/wiki"


def formatted_strings() -> str:
    console = Console(record=True)
    commands_table = Table(show_header=False, show_edge=False, show_lines=False, box=None)
    for item in strings.items():
        commands_table.add_row(*item)

    with console.capture() as capture:
        console.print(commands_table)
    return capture.get()
