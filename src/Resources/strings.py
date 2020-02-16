from terminaltables import SingleTable


strings = {
    "vstart": "Start a new Kathara machine",
    "vclean": "Stop a single Kathara machine",
    "vconfig": "Attach network interfaces to a running Kathara machine",
    "lstart": "Start a Kathara lab",
    "lclean": "Stop a Kathara lab",
    "linfo": "Show information about a Kathara lab",
    "lrestart": "Restart a Kathara lab",
    "ltest": "Test a Kathara lab",
    "lconfig": "Attach network interfaces to a running Kathara machine in a Kathara lab",
    "connect": "Connect to a Kathara machine",
    "wipe": "Delete all Kathara machines and links, optionally also delete settings",
    "list": "Show all running Kathara machines of the current user",
    "settings": "Show and edit Kathara settings",
    "check": "Check your system environment"
}

wiki_description = "For examples and further information visit: https://github.com/KatharaFramework/Kathara/wiki"


def formatted_strings():
    commands = []
    for item in strings.items():
        commands.append(list(item))

    commands_table = SingleTable(commands)
    commands_table.inner_heading_row_border = False
    commands_table.outer_border = False
    commands_table.inner_column_border = False

    return commands_table.table
