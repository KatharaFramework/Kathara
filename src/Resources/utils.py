import base64
import hashlib
import importlib
import math
import os
import re
import shutil
import sys
import tarfile
import tempfile
from io import BytesIO
from itertools import islice
from sys import platform as _platform

from binaryornot.check import is_binary

from .setting.Setting import EXCLUDED_FILES
from .trdparty.consolemenu import PromptUtils, Screen

# Platforms constants definition.
MAC_OS = "darwin"
WINDOWS = "win32"
LINUX = "linux"
LINUX2 = "linux2"


def check_python_version():
    if sys.version_info < (3, 0):
        print("Python version should be greater than 3.0")
        sys.exit(1)


def class_for_name(module_name, class_name):
    m = importlib.import_module(module_name + "." + class_name)
    return getattr(m, class_name)


def generate_urlsafe_hash(string):
    string = re.sub(r'[^\x00-\x7F]+', '', string)
    return base64.urlsafe_b64encode(hashlib.md5(string.encode('utf-8', errors='ignore')).digest())[:-2].decode('utf-8')


def get_absolute_path(path):
    abs_path = os.path.abspath(path)
    return abs_path if not os.path.islink(abs_path) else os.readlink(abs_path)


def get_executable_path(exec_path):
    # If it is in the path, everything is ok
    if shutil.which(exec_path):
        return exec_path

    exec_abs_path = get_absolute_path(exec_path)

    if os.path.exists(exec_abs_path):
        # If it is launched as a python script
        if exec_path.endswith(".py"):
            # Prepend python in windows because it has no shebang
            return exec_by_platform(lambda: exec_abs_path, lambda: "python %s" % exec_abs_path, lambda: exec_abs_path)
        else:
            # Maybe the executable is not in path, but is still a binary file
            return exec_abs_path

    return None


def format_headers(message):
    footer = "=============================="
    half_message = int((len(message) / 2) + 1)
    second_half_message = half_message

    if len(message) % 2 == 0:
        second_half_message -= 1

    return footer[half_message:] + " " + message + " " + footer[second_half_message:]


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
    tempdir = exec_by_platform(tempfile.gettempdir, tempfile.gettempdir, lambda: "/%s" % get_absolute_path("/tmp"))

    vlab_directory = os.path.join(tempdir, "kathara_vlab")
    if not os.path.isdir(vlab_directory) and force_creation:
        os.mkdir(vlab_directory)

    return vlab_directory


def confirmation_prompt(prompt_string, callback_yes, callback_no):
    prompt_utils = PromptUtils(Screen())
    answer = prompt_utils.prompt_for_bilateral_choice(prompt_string, 'y', 'n')

    if answer == "n":
        return callback_no()

    return callback_yes()


def convert_win_2_linux(filename):
    if not is_binary(filename):
        file_content = open(filename, mode='r', encoding='utf-8-sig').read()
        return file_content.replace("\n\r", "\n").encode('utf-8')


def pack_file_for_tar(filename, arcname):
    file_content_patched = convert_win_2_linux(filename)

    file_content = BytesIO(file_content_patched)
    tarinfo = tarfile.TarInfo(arcname.replace("\\", "/"))   # Tar files must have Linux-style paths
    tarinfo.size = len(file_content_patched)

    return tarinfo, file_content


def is_excluded_file(path):
    _, filename = os.path.split(path)

    return filename in EXCLUDED_FILES


def get_current_user_home():
    def passwd_home():
        user_info = get_current_user_info()
        return user_info.pw_dir

    def default_home():
        return os.path.expanduser('~')

    return exec_by_platform(passwd_home, default_home, default_home)


def get_current_user_uid_gid():
    def unix():
        user_info = get_current_user_info()
        return user_info.pw_uid, user_info.pw_gid

    return exec_by_platform(unix, lambda: (None, None), unix)


def get_current_user_name():
    def unix():
        user_info = get_current_user_info()
        return user_info.pw_name

    def windows():
        import getpass
        return getpass.getuser()

    return exec_by_platform(unix, windows, unix)


def get_current_user_info():
    def passwd_info():
        import pwd
        user_id = os.getuid()

        # It's root, take the real user from env variable
        if user_id == 0:
            # If it's a sudoer, take the SUDO_UID and use it as user_id variable
            # If not, keep using the user_id = 0
            real_user_id = os.environ.get("SUDO_UID")

            if real_user_id:
                user_id = int(real_user_id)

        return pwd.getpwuid(user_id)

    return exec_by_platform(passwd_info, lambda: None, passwd_info)


def re_search_fail(expression, line):
    matches = re.search(expression, line)

    if not matches:
        raise ValueError()

    return matches


def list_chunks(iterable, size):
    it = iter(iterable)
    item = list(islice(it, size))
    while item:
        yield item
        item = list(islice(it, size))