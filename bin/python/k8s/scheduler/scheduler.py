import importlib


def load_scheduler_from_config():
    # TODO: Load scheduler from config
    return "hierarchical_clustering"


def schedule(machines):
    selected_scheduler = load_scheduler_from_config()

    print "Current scheduler is: " + selected_scheduler
    scheduler_module = importlib.import_module("k8s.scheduler." + selected_scheduler + "_scheduler")
    return scheduler_module.get_constraints_for_lab(machines)
