import base64
import hashlib
import importlib
import math
import os
import re
import tempfile
from sys import platform as _platform

from classes.setting.Setting import VLAB_NAME

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
    return base64.urlsafe_b64encode(hashlib.md5(string.encode('utf-8', errors='ignore')).digest())[:-2].decode('utf-8')


def get_absolute_path(path):
    return os.path.abspath(path)


def exec_by_platform(fun_linux, fun_windows, fun_mac):
    if _platform == LINUX or _platform == LINUX2:
        return fun_linux()
    elif _platform == WINDOWS:
        return fun_windows()
    elif _platform == MAC_OS:
        return fun_mac()


def human_readable_bytes(size_bytes):
    if size_bytes == 0:
        return "0 B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)

    return "%s %s" % (s, size_name[i])


def get_vlab_temp_path(force_creation=True):
    vlab_directory = os.path.join(tempfile.gettempdir(), VLAB_NAME)
    if not os.path.isdir(vlab_directory) and force_creation:
        os.mkdir(vlab_directory)

    return vlab_directory


def confirmation_prompt(prompt_string, callback_yes, callback_no):
    answer = None
    while answer not in ["y", "yes", "Y", "YES", "n", "no", "N", "NO"]:
        answer = input("%s [y/n] " % prompt_string)

        if answer in ["n", "no", "NO"]:
            return callback_no()

    return callback_yes()
