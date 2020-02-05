import errno
import fcntl
import json
import os
import select
import signal
import struct
import sys
import termios
import tty

from kubernetes.stream.ws_client import RESIZE_CHANNEL, ERROR_CHANNEL

# The following escape codes are xterm codes.
# See http://rtfm.etla.org/xterm/ctlseq.html for more.
START_ALTERNATE_MODE = set('\x1b[?{0}h'.format(i) for i in ('1049', '47', '1047'))
END_ALTERNATE_MODE = set('\x1b[?{0}l'.format(i) for i in ('1049', '47', '1047'))
ALTERNATE_MODE_FLAGS = tuple(START_ALTERNATE_MODE) + tuple(END_ALTERNATE_MODE)


class Interceptor(object):
    """
    This class does the actual work of the pseudo terminal.
    """
    def __init__(self, k8s_stream=None):
        self.k8s_stream = k8s_stream
        self.master_fd = None
        self.mode = None

    def start(self):
        self.master_fd = sys.stdin.fileno()

        old_handler = signal.signal(signal.SIGWINCH, self._signal_winch)
        try:
            self.mode = tty.tcgetattr(self.master_fd)
            tty.setraw(self.master_fd)
            tty_started = True
        except tty.error:
            tty_started = False

        if tty_started:
            self._init_fd()

            try:
                self._copy()
            finally:
                tty.tcsetattr(self.master_fd, tty.TCSAFLUSH, self.mode)

        self.k8s_stream.close()
        self.k8s_stream = None

        signal.signal(signal.SIGWINCH, old_handler)

    def _init_fd(self):
        """
        Called once when the pty is first set up.
        """
        self._set_pty_size()

    def _signal_winch(self, signum, frame):
        """
        Signal handler for SIGWINCH - window size has changed.
        """
        self._set_pty_size()

    def _set_pty_size(self):
        """
        Sets the window size of the child pty based on the window size of our own controlling terminal.
        """
        packed = fcntl.ioctl(self.master_fd,
                             termios.TIOCGWINSZ,
                             struct.pack('HHHH', 0, 0, 0, 0)
                             )

        rows, cols, _, _ = struct.unpack('HHHH', packed)

        self.k8s_stream.write_channel(RESIZE_CHANNEL, json.dumps({"Height": rows, "Width": cols}))

    def _copy(self):
        """
        Main select loop. Passes all data to self.master_read() or self.stdin_read().
        """
        assert self.k8s_stream is not None
        k8s_stream = self.k8s_stream
        while True:
            try:
                read_ready, _, _ = select.select([self.master_fd, k8s_stream.sock.sock], [], [], 60)
            except select.error as e:
                if e.errno == errno.EINTR:
                    continue

            if self.master_fd in read_ready:
                data = os.read(self.master_fd, 4096)
                self.stdin_read(data)
            if k8s_stream.sock.sock in read_ready:
                if k8s_stream.peek_stdout():
                    self.master_read(k8s_stream.read_stdout())

                if k8s_stream.peek_channel(ERROR_CHANNEL):
                    break

    def write_stdout(self, data):
        """
        Writes to stdout as if the child process had written the data.
        """
        os.write(self.master_fd, data.encode('utf-8'))

    def write_master(self, data):
        """
        Writes to the child process from its controlling terminal.
        """
        assert self.k8s_stream is not None
        self.k8s_stream.write_stdin(data.decode('utf-8'))

    def master_read(self, data):
        """
        Called when there is data to be sent from the child process back to
               the user.
        """
        self.write_stdout(data)

    def stdin_read(self, data):
        """
        Called when there is data to be sent from the user/controlling
               terminal down to the child process.
        """
        self.write_master(data)
