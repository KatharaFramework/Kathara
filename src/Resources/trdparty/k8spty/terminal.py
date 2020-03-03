import errno
import json
import os
import select
import signal
import struct
import sys
import tty

import fcntl
import termios
from kubernetes.stream.ws_client import RESIZE_CHANNEL, ERROR_CHANNEL

# The following escape codes are xterm codes.
# See http://rtfm.etla.org/xterm/ctlseq.html for more.
START_ALTERNATE_MODE = set('\x1b[?{0}h'.format(i) for i in ('1049', '47', '1047'))
END_ALTERNATE_MODE = set('\x1b[?{0}l'.format(i) for i in ('1049', '47', '1047'))
ALTERNATE_MODE_FLAGS = tuple(START_ALTERNATE_MODE) + tuple(END_ALTERNATE_MODE)


class KubernetesTerminal(object):
    __slots__ = ['k8s_stream', 'stdin_fd', 'stdout_fd', 'mode']

    def __init__(self, k8s_stream=None):
        self.k8s_stream = k8s_stream

        self.stdin_fd = None
        self.stdout_fd = None

        self.mode = None

    def start(self):
        self.stdin_fd = sys.stdin.fileno()
        self.stdout_fd = sys.stdout.fileno()

        old_handler = signal.signal(signal.SIGWINCH, self._signal_winch)
        try:
            self.mode = tty.tcgetattr(self.stdin_fd)
            tty.setraw(self.stdin_fd)
            tty_started = True
        except tty.error:
            tty_started = False

        if tty_started:
            self._init_fd()

            try:
                self._copy()
            finally:
                tty.tcsetattr(self.stdin_fd, tty.TCSAFLUSH, self.mode)

        self.k8s_stream.close()
        self.k8s_stream = None

        signal.signal(signal.SIGWINCH, old_handler)

    def _init_fd(self):
        self._set_pty_size()

    def _signal_winch(self, signum, frame):
        self._set_pty_size()

    def _set_pty_size(self):
        packed = fcntl.ioctl(self.stdin_fd,
                             termios.TIOCGWINSZ,
                             struct.pack('HHHH', 0, 0, 0, 0)
                             )

        rows, cols, _, _ = struct.unpack('HHHH', packed)

        self.k8s_stream.write_channel(RESIZE_CHANNEL, json.dumps({"Height": rows, "Width": cols}))

    def _copy(self):
        assert self.k8s_stream is not None
        k8s_stream = self.k8s_stream
        while True:
            try:
                read_ready, _, _ = select.select([self.stdin_fd, k8s_stream.sock.sock], [], [], 60)
            except select.error as e:
                if e.errno == errno.EINTR:
                    continue

            if self.stdin_fd in read_ready:
                data = os.read(self.stdin_fd, 4096)
                self.stdin_read(data)
            if k8s_stream.sock.sock in read_ready:
                if k8s_stream.peek_stdout():
                    self.master_read(k8s_stream.read_stdout())

                if k8s_stream.peek_channel(ERROR_CHANNEL):
                    break

    def master_read(self, data):
        os.write(self.stdout_fd, data.encode('utf-8'))

    def stdin_read(self, data):
        assert self.k8s_stream is not None
        self.k8s_stream.write_stdin(data.decode('utf-8'))
