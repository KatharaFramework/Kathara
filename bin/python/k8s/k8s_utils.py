import re


def build_k8s_name(resource_name, prefix=""):
    # K8s names should be only alphanumeric lowercase + "-" + "."
    new_resource_name = resource_name.lower()
    new_resource_name = re.sub('[^0-9a-z\-\.]+', '', new_resource_name)
    return (prefix + "-" if prefix != "" else "") + new_resource_name
