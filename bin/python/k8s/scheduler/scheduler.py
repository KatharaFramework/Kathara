import importlib


def load_scheduler_config():
    return {
        "type": "spectral_clustering",
        "use_semantic": True
    }


def schedule(machines, lab_path):
    scheduler_config = load_scheduler_config()

    print "Current scheduler is: " + scheduler_config["type"]
    scheduler_module = importlib.import_module("k8s.scheduler." + scheduler_config["type"] + "_scheduler")
    return scheduler_module.get_constraints_for_lab(machines, lab_path, use_semantic=scheduler_config["use_semantic"])
