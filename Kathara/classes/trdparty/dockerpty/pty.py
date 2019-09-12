# dockerpty: pty.py
#
# Copyright 2014 Chris Corbyn <chris@w3style.co.uk>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import signal
import warnings
from ssl import SSLError

# import classes.trdparty.dockerpty as dockerpty
from classes.trdparty.dockerpty import io
from classes.trdparty.dockerpty import tty


class WINCHHandler(object):
    """
    WINCH Signal handler to keep the PTY correctly sized.
    """

    def __init__(self, pty):
        """
        Initialize a new WINCH handler for the given PTY.

        Initializing a handler has no immediate side-effects. The `start()`
        method must be invoked for the signals to be trapped.
        """

        self.pty = pty
        self.original_handler = None

    def __enter__(self):
        """
        Invoked on entering a `with` block.
        """

        self.start()
        return self

    def __exit__(self, *_):
        """
        Invoked on exiting a `with` block.
        """

        self.stop()

    def start(self):
        """
        Start trapping WINCH signals and resizing the PTY.

        This method saves the previous WINCH handler so it can be restored on
        `stop()`.
        """

        def handle(signum, frame):
            if signum == signal.SIGWINCH:
                self.pty.resize()

        self.original_handler = signal.signal(signal.SIGWINCH, handle)

    def stop(self):
        """
        Stop trapping WINCH signals and restore the previous WINCH handler.
        """

        if self.original_handler is not None:
            signal.signal(signal.SIGWINCH, self.original_handler)


class PseudoTerminal(object):
    """
    Wraps the pseudo-TTY (PTY) allocated to a docker container.

    The PTY is managed via the current process' TTY until it is closed.

    Care is taken to ensure all file descriptors are restored on exit. For
    example, you can attach to a running container from within a Python REPL
    and when the container exits, the user will be returned to the Python REPL
    without adverse effects.
    """

    def __init__(self, client, stream, exec_id):
        """
        Initialize the PTY using the docker.Client instance and container dict.
        """
        self.stream = io.Stream(stream)
        self.raw = None
        self.exec_id = exec_id
        self.client = client

    def do_resize(self, height, width):
        """
        resize pty of an execed process
        """
        self.client.api.exec_resize(self.exec_id, height=height, width=width)

    def start(self, sockets=None):
        pumps = []

        pumps.append(io.Pump(io.Stream(sys.stdin), self.stream, wait_for_output=False))

        pumps.append(io.Pump(self.stream, io.Stream(sys.stdout), propagate_close=False))

        flags = [p.set_blocking(False) for p in pumps]

        try:
            with WINCHHandler(self):
                self._hijack_tty(pumps)
        finally:
            if flags:
                for (pump, flag) in zip(pumps, flags):
                    io.set_blocking(pump, flag)


    def resize(self, size=None):
        """
        Resize the container's PTY.

        If `size` is not None, it must be a tuple of (height,width), otherwise
        it will be determined by the size of the current TTY.
        """

        if not self.israw():
            return

        size = size or tty.size(sys.stdout)

        if size is not None:
            rows, cols = size
            try:
                self.do_resize(height=rows, width=cols)
            except IOError:  # Container already exited
                pass


    def israw(self):
        """
        Returns True if the PTY should operate in raw mode.

        If the exec was not started with tty=True, this will return False.
        """

        if self.raw is None:
            self.raw = sys.stdout.isatty()

        return self.raw

    def _hijack_tty(self, pumps):
        with tty.Terminal(sys.stdin, raw=self.israw()):
            self.resize()
            while True:
                read_pumps = [p for p in pumps if not p.eof]
                write_streams = [p.to_stream for p in pumps if p.to_stream.needs_write()]

                read_ready, write_ready = io.select(read_pumps, write_streams, timeout=60)
                try:
                    for write_stream in write_ready:
                        write_stream.do_write()

                    for pump in read_ready:
                        pump.flush()

                    if all([p.is_done() for p in pumps]):
                        break

                except SSLError as e:
                    if 'The operation did not complete' not in e.strerror:
                        raise e
