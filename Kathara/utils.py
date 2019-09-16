import base64
import hashlib
import importlib
import os
import re
from sys import platform as _platform

# Platforms constants definition.
MAC_OS = "darwin"
WINDOWS = "win32"
LINUX = "linux"
LINUX2 = "linux2"


def class_for_name(module_name, class_name):
    m = importlib.import_module(module_name + "." + class_name)
    return getattr(m, class_name)


def generate_urlsafe_hash(string):
    string = re.sub(r'[^\x00-\x7F]+', '', string)
    return str(base64.urlsafe_b64encode(hashlib.md5(string.encode('utf-8', errors='ignore')).digest())[:-2])


def get_absolute_path(path):
    return os.path.abspath(path)


def exec_by_platform(fun_linux, fun_windows, fun_mac):
    if _platform == LINUX or _platform == LINUX2:
        fun_linux()
    elif _platform == WINDOWS:
        fun_windows()
    elif _platform == MAC_OS:
        fun_mac()
