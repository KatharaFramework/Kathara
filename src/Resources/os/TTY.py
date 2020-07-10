import sys

import pyuv


class Terminal(object):
    __slots__ = ['fd', '_loop', '_system_stdin', '_system_stdout', '_external_tty']

    def __init__(self, fd):
        self.fd = fd

        self._loop = None
        self._system_stdin = None
        self._system_stdout = None
        self._external_tty = None

    def start(self):
        self._loop = pyuv.Loop.default_loop()

        self._system_stdin = pyuv.TTY(self._loop, sys.stdin.fileno(), True)
        self._system_stdin.set_mode(1)
        self._system_stdin.start_read(self._write_on_external_tty())

        self._system_stdout = pyuv.TTY(self._loop, sys.stdout.fileno(), True)

        self._external_tty = pyuv.TTY(self._loop, self.fd, True)
        self._external_tty.start_read(self._handle_external_tty())

        self._loop.run()

        pyuv.TTY.reset_mode()

    def close(self):
        self._system_stdin.set_mode(0)
        self._system_stdin.close()
        self._external_tty.close()
        self._system_stdout.close()
        self._loop.stop()

    def _write_on_external_tty(self):
        def write_on_external_tty(handle, data, error):
            self._external_tty.write(data)

        return write_on_external_tty

    def _handle_external_tty(self):
        def handle_external_tty(handle, data, error):
            if data:
                self._system_stdout.write(data)
            else:
                self.close()

        return handle_external_tty
