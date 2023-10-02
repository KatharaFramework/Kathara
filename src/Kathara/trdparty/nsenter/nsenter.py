"""
nsenter - run program with namespaces of other processes
Adapted from: https://github.com/zalando/python-nsenter
"""

import ctypes
import ctypes.util
import errno
import logging
import os
from contextlib import ExitStack
from pathlib import Path
from typing import Union, Optional, List

NAMESPACE_NAMES = frozenset(['mnt', 'ipc', 'net', 'pid', 'user', 'uts'])


class Namespace(object):
    """A context manager for entering namespaces

    Args:
        pid: The PID for the owner of the namespace to enter, or an absolute
             path to a file which represents a namespace handle.

        ns_type: The type of namespace to enter must be one of
                 mnt ipc net pid user uts.  If pid is an absolute path, this
                 much match the type of namespace it represents

        proc: The path to the /proc file system.  If running in a container
              the host proc file system may be binded mounted in a different
              location

    Raises:
        IOError: A non existent PID was provided
        ValueError: An improper ns_type was provided
        OSError: Unable to enter or exit the namespace

    Example:
        with Namespace(916, 'net'):
            #do something in the namespace
            pass

        with Namespace('/var/run/netns/foo', 'net'):
            #do something in the namespace
            pass
    """

    _log = logging.getLogger(__name__)
    _libc = ctypes.CDLL(ctypes.util.find_library('c'), use_errno=True)

    def __init__(self, pid, ns_type, proc='/proc'):
        if ns_type not in NAMESPACE_NAMES:
            raise ValueError('ns_type must be one of {0}'.format(
                ', '.join(NAMESPACE_NAMES)
            ))

        self.pid = pid
        self.ns_type = ns_type
        self.proc = proc

        # if it's numeric, then it's a pid, else assume it's a path
        try:
            pid = int(pid)
            self.target_fd = self._nsfd(pid, ns_type).open()
        except ValueError:
            self.target_fd = Path(pid).open()

        self.target_fileno = self.target_fd.fileno()

        self.parent_fd = self._nsfd('self', ns_type).open()
        self.parent_fileno = self.parent_fd.fileno()

    __init__.__annotations__ = {'pid': str, 'ns_type': str}

    def _nsfd(self, pid, ns_type):
        """Utility method to build a pathlib.Path instance pointing at the
        requested namespace entry

        Args:
            pid: The PID
            ns_type: The namespace type to enter

        Returns:
             pathlib.Path pointing to the /proc namespace entry
        """
        return Path(self.proc) / str(pid) / 'ns' / ns_type

    _nsfd.__annotations__ = {'process': str, 'ns_type': str, 'return': Path}

    def _close_files(self):
        """Utility method to close our open file handles"""
        try:
            self.target_fd.close()
        except:
            pass

        if self.parent_fd is not None:
            self.parent_fd.close()

    def __enter__(self):
        self._log.debug('Entering %s namespace %s', self.ns_type, self.pid)

        if self._libc.setns(self.target_fileno, 0) == -1:
            e = ctypes.get_errno()
            self._close_files()
            raise OSError(e, errno.errorcode[e])

    def __exit__(self, type, value, tb):
        self._log.debug('Leaving %s namespace %s', self.ns_type, self.pid)

        if self._libc.setns(self.parent_fileno, 0) == -1:
            e = ctypes.get_errno()
            self._close_files()
            raise OSError(e, errno.errorcode[e])

        self._close_files()


def nsenter(target: Union[str, int], command: str, proc: str = "/proc",
            ns_types: Optional[List[str]] = None, all_ns_types: bool = True):
    """Enter namespace, adapted from main() function to work from Python.

    Args:
        target (Union[str, int]: The PID for the owner of the namespace to enter, or an absolute
            path to a file which represents a namespace handle.
        command (str): The command to run inside the namespace.
        proc (str): The path to the /proc file system.  If running in a container the host proc file system may be
            bind-mounted in a different location.
        ns_types (Optional[str]): The type of namespaces to enter. Must be one of:
            mnt ipc net pid user uts. If target is an absolute path, much match the type of namespace it represents.
            Can be used alternatively to all.
        all_ns_types (bool): Enable all types of namespaces. Can be used alternatively to ns_types. Default is True.

    Raises:
        ValueError: Neither ns_types or all was provided.
        OSError: Unable to enter or exit the namespace.
    """
    if ns_types is None:
        ns_types = []

    if not ns_types and not all_ns_types:
        raise ValueError('You must specify at least one namespace.')

    # Disable all_ns_types in case there is the list.
    if ns_types:
        all_ns_types = False

    try:
        with ExitStack() as stack:
            namespaces = []
            for ns in NAMESPACE_NAMES:
                if ns in ns_types or all_ns_types:
                    namespaces.append(Namespace(target, ns, proc=proc))

            for ns in namespaces:
                stack.enter_context(ns)

            # Added: chroot in the namespace root, copied from nsenter util
            wd_fd = os.open(".", os.O_RDONLY)
            host_root_fd = os.open("/", os.O_RDONLY)
            root_fd = os.open(os.path.join(proc, str(target), "root"), os.O_RDONLY)

            os.fchdir(root_fd)
            os.chroot(".")
            os.close(root_fd)

            os.system(command)

        os.fchdir(host_root_fd)
        os.chroot(".")
        os.fchdir(wd_fd)

        os.close(host_root_fd)
        os.close(wd_fd)
    except OSError as exc:
        raise OSError('Unable to enter {0} namespace: {1}.'.format(ns.ns_type, exc))
