import base64
import hashlib
import importlib
import io
import logging
import math
import os
import re
import shutil
import sys
import tarfile
import tempfile
from io import BytesIO
from itertools import islice
from multiprocessing import cpu_count
from platform import node, machine
from sys import platform as _platform
from typing import Any, Optional, Match, Generator, List, Callable, Union, Dict, Iterable

from binaryornot.check import is_binary
from slug import slug

from .trdparty.consolemenu import PromptUtils, Screen

# Platforms constants definition.
MAC_OS: str = "darwin"
WINDOWS: str = "win32"
LINUX: str = "linux"
LINUX2: str = "linux2"

# List of ignored files
EXCLUDED_FILES: List[str] = ['.DS_Store']

# True if launched from CLI
CLI_ENV: bool = False

# Reserved names for devices
RESERVED_MACHINE_NAMES: List[str] = ['shared', '_test']


# Generic Functions
def check_python_version() -> None:
    if sys.version_info < (3, 0):
        logging.critical("Python version should be greater than 3.0")
        sys.exit(1)


def class_for_name(module_name: str, class_name: str) -> Any:
    m = importlib.import_module(module_name + "." + class_name)
    return getattr(m, class_name)


def generate_urlsafe_hash(string: str) -> str:
    string = re.sub(r'[^\x00-\x7F]+', '', string)
    return base64.urlsafe_b64encode(hashlib.md5(string.encode('utf-8', errors='ignore')).digest())[:-2] \
        .decode('utf-8') \
        .replace('-', '').replace('_', '')


def get_absolute_path(path: str) -> str:
    abs_path = os.path.realpath(path)
    return abs_path if not os.path.islink(abs_path) else os.readlink(abs_path)


def get_executable_path(exec_path: str) -> Optional[str]:
    exec_abs_path = get_absolute_path(exec_path)

    if os.path.exists(exec_abs_path) and os.path.isfile(exec_abs_path):
        # If kathara is launched as a python script
        exec_abs_path = "\"" + exec_abs_path + "\""
        if exec_path.endswith(".py"):
            # Prepend python in windows because it has no shebang
            return exec_by_platform(lambda: exec_abs_path,
                                    lambda: "%s %s" % (sys.executable, exec_abs_path),
                                    lambda: "%s %s" % (sys.executable, exec_abs_path)
                                    )
        else:
            # Maybe the executable is not in path, but is still a binary file
            return exec_abs_path
    else:
        # If kathara is in the path, return the absolute path of kathara
        which_path = shutil.which(exec_path)
        if which_path:
            return "\"" + which_path + "\""

    return None


def re_search_fail(expression: str, line: str) -> Match:
    matches = re.search(expression, line)

    if not matches:
        raise ValueError()

    return matches


def list_chunks(iterable: List, size: int) -> Generator:
    it = iter(iterable)
    item = list(islice(it, size))
    while item:
        yield item
        item = list(islice(it, size))


def chunk_list(iterable: Union[List, Iterable], size: int) -> List[List]:
    return [iterable] if len(iterable) < size else list_chunks(iterable, size)


def confirmation_prompt(prompt_string: str, callback_yes: Callable, callback_no: Callable) -> Any:
    prompt_utils = PromptUtils(Screen())
    answer = prompt_utils.prompt_for_bilateral_choice(prompt_string, 'y', 'n')

    if answer == "n":
        return callback_no()

    return callback_yes()


def get_pool_size() -> int:
    return cpu_count()


# Platform Specific Functions
def is_platform(desired_platform: str) -> bool:
    return _platform == desired_platform


def exec_by_platform(fun_linux: Callable, fun_windows: Callable, fun_mac: Callable) -> Any:
    if _platform == LINUX or _platform == LINUX2:
        return fun_linux()
    elif _platform == WINDOWS:
        return fun_windows()
    elif _platform == MAC_OS:
        return fun_mac()


# Architecture Test
def get_architecture() -> str:
    architecture = machine().lower()

    logging.debug("Machine architecture is `%s`." % architecture)

    if architecture == "x86_64" or architecture == "amd64":
        return "amd64"
    elif architecture == "i686":
        return "386"
    elif architecture in ['arm64', 'aarch64']:
        return "arm64"
    elif architecture == "armv7l":
        return "armv7"
    elif architecture == "armv6l":
        return "armv6"
    else:
        raise Exception("Not implemented for %s." % architecture)


def convert_win_2_linux(filename: str) -> bytes:
    if not is_binary(filename):
        file_content = open(filename, mode='r', encoding='utf-8-sig').read()
        return file_content.replace("\n\r", "\n").encode('utf-8')

    return open(filename, mode='rb').read()


def is_admin() -> bool:
    def unix_root():
        return os.getuid() == 0

    def windows_admin():
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0

    return exec_by_platform(unix_root, windows_admin, unix_root)


def get_current_user_home() -> str:
    def passwd_home():
        user_info = get_current_user_info()
        return user_info.pw_dir

    def default_home():
        return os.path.expanduser('~')

    return exec_by_platform(passwd_home, default_home, default_home)


def get_current_user_uid_gid() -> (int, int):
    def unix():
        user_info = get_current_user_info()
        return user_info.pw_uid, user_info.pw_gid

    return exec_by_platform(unix, lambda: (None, None), unix)


def get_current_user_name() -> str:
    hostname = generate_urlsafe_hash(node())

    def unix():
        user_info = get_current_user_info()
        return user_info.pw_name

    def windows():
        import getpass
        return getpass.getuser()

    return slug("%s-%s" % (exec_by_platform(unix, windows, unix), hostname))


def get_current_user_info() -> Any:
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


# Formatting Functions
def format_headers(message: str = "") -> str:
    footer = "=============================="
    half_message = int((len(message) / 2) + 1)
    second_half_message = half_message

    if len(message) % 2 == 0:
        second_half_message -= 1

    message = " " + message + " " if message != "" else "=="
    return footer[half_message:] + message + footer[second_half_message:]


def human_readable_bytes(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"

    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)

    return "%s %s" % (s, size_name[i])


# Lab Functions
def get_lab_temp_path(lab_name: str, force_creation: bool = True) -> str:
    def windows_path():
        import win32file
        return win32file.GetLongPathName(tempfile.gettempdir())

    tempdir = exec_by_platform(tempfile.gettempdir,
                               windows_path,
                               lambda: re.sub(r"/+", "/", "/%s" % get_absolute_path("/tmp"))
                               )
    lab_temp_directory = os.path.join(tempdir, lab_name)
    if not os.path.isdir(lab_temp_directory) and force_creation:
        os.mkdir(lab_temp_directory)

    return lab_temp_directory


def get_vlab_temp_path(force_creation: bool = True) -> str:
    return get_lab_temp_path("kathara_vlab", force_creation=force_creation)


def pack_file_for_tar(file_obj: Union[str, io.IOBase], arc_name: str) -> (tarfile.TarInfo, bytes):
    if isinstance(file_obj, str):
        file_content_patched = convert_win_2_linux(file_obj)
        file_content = BytesIO(file_content_patched)
        filesize = len(file_content_patched)
    elif isinstance(file_obj, io.IOBase):
        file_content = file_obj.read()
        file_content = BytesIO(file_content.encode('utf-8') if isinstance(file_obj, io.TextIOBase) else file_content)
        file_obj.seek(0, 2)
        filesize = file_obj.tell()
        file_obj.seek(0)
    else:
        raise ValueError("File type %s not supported" % type(file_obj))

    tarinfo = tarfile.TarInfo(arc_name.replace("\\", "/"))  # Tar files must have Linux-style paths
    tarinfo.size = filesize

    return tarinfo, file_content


def pack_files_for_tar(guest_to_host: Dict) -> bytes:
    with tempfile.NamedTemporaryFile(mode='wb+', suffix='.tar.gz') as temp_file:
        with tarfile.open(fileobj=temp_file, mode='w:gz') as tar_file:
            for path, file_obj in guest_to_host.items():
                tar_info, file_content = pack_file_for_tar(file_obj, arc_name=path)
                tar_file.addfile(tar_info, file_content)

        temp_file.seek(0)

        tar_data = temp_file.read()

    return tar_data


def is_excluded_file(path: str) -> bool:
    _, filename = os.path.split(path)

    return filename in EXCLUDED_FILES
