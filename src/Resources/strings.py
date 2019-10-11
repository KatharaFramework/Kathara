strings = {
    "vstart": "Start a new Kathara machine",
    "vclean": "Stop a single Kathara machine",
    "vconfig": "Attach network interfaces to a running Kathara machine",
    "lstart": "Start a Kathara lab",
    "lclean": "Stop a Kathara lab",
    "linfo": "Show information about a Kathara lab",
    "lrestart": "Restart a Kathara lab",
    "ltest": "Test a Kathara lab",
    "connect": "Connect to a Kathara machine",
    "wipe": "Delete all Kathara machines and links, optionally also delete settings",
    "list": "Show all running Kathara machines",
    "settings": "Show and edit Kathara settings",
    "check": "Check your system environment"
}

wiki_description = "For examples and further information visit: https://github.com/KatharaFramework/Kathara/wiki"


def formatted_strings():
    def tab_formatting(string):
        return "\t\t" if len(string) < 8 else "\t"

    return "\n".join(["\t%s%s%s" % (k, tab_formatting(k), v) for (k, v) in strings.items()])
