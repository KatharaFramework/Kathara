import asyncio
from typing import Optional

from .IConsoleAdapter import IConsoleAdapter
from .ITerminalSession import ITerminalSession
from .....utils import exec_by_platform


class TerminalRunner(object):
    """Bridge class between a console adapter and a terminal session.

    Attributes:
        console (IConsoleAdapter): OS-specific console adapter.
        session (ITerminalSession): Wrapper of the manager terminal session.
        _loop (Optional[asyncio.AbstractEventLoop]): Event loop from asyncio used by the runner.
        _closed (bool): Boolean flag indicating whether the runner is terminated.
        _tasks (list[asyncio.Task]): List of asyncio tasks created by the runner.
        _session_fd (Optional[int]): File descriptor from session.fileno() when available.
    """
    __slots__ = ["console", "session", "_loop", "_closed", "_tasks", "_session_fd"]

    def __init__(self, console: IConsoleAdapter, session: ITerminalSession) -> None:
        self.console: IConsoleAdapter = console
        self.session: ITerminalSession = session

        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self._closed: bool = False

        self._tasks: list[asyncio.Task] = []
        self._session_fd: Optional[int] = None

    def start(self) -> None:
        """Start the bridge and block until the runner stops.

        This method:
            - creates and sets a new asyncio loop
            - enters console raw mode
            - starts watching resize and input
            - starts pumping session output to stdout
            - runs the loop forever until close() is invoked

        Returns:
            None
        """
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self.console.enter_raw()
        self.console.watch_resize(self._loop, self._on_resize)

        self.console.install_input_reader(self._loop, self._on_stdin_bytes, self.close)
        self._start_stdout()

        try:
            self._loop.run_forever()
        finally:
            self._loop.close()

    def _on_resize(self, cols: int, rows: int) -> None:
        """Handle terminal resize events.

        Args:
            cols (int): Terminal width in columns.
            rows (int): Terminal height in rows.

        Returns:
            None
        """
        if self._closed:
            return

        try:
            self.session.resize(cols, rows)
        except Exception:
            self.close()

    def _on_stdin_bytes(self, data: bytes) -> None:
        """Handle bytes received from local stdin.

        Args:
            data (bytes): Data read from stdin.

        Returns:
            None
        """
        if self._closed:
            return

        if not data:
            self.close()
            return

        try:
            self.session.write(data)
        except Exception:
            self.close()

    def _on_session_readable(self) -> None:
        """Handle readiness notification for session output (fd-based). Called when the session fd becomes readable.

        Returns:
            None
        """
        if self._closed:
            return

        try:
            data = self.session.read(4096)
        except Exception:
            self.close()
            return

        if not data:
            self.close()
            return

        try:
            self.console.write_stdout(data)
        except Exception:
            self.close()
            return

    async def _threaded_stdout(self) -> None:
        """Continuously read session output in a thread executor and write to stdout.

        This is used when:
            - the session does not expose a file descriptor (fileno() is None), or
            - on Windows where fd-based readers are not unavailable.

        Returns:
            None
        """
        while not self._closed:
            try:
                data = await self._loop.run_in_executor(None, self.session.read, 4096)
            except Exception:
                self.close()
                return

            if self._closed:
                return

            if not data:
                await asyncio.sleep(0.03)
                continue

            try:
                self.console.write_stdout(data)
            except Exception:
                self.close()
                return

    def _start_stdout(self) -> None:
        """Start pumping session output to local stdout using an OS-specify strategy.

        Returns:
            None
        """

        def unix():
            self._session_fd = self.session.fileno()
            if self._session_fd is None:
                self._tasks.append(self._loop.create_task(self._threaded_stdout()))
                return

            self._loop.add_reader(self._session_fd, self._on_session_readable)

        def windows():
            self._tasks.append(self._loop.create_task(self._threaded_stdout()))

        exec_by_platform(unix, windows, unix)

    def close(self) -> None:
        """Stop the runner and perform cleanup.

        Returns:
            None
        """
        if self._closed or self._loop is None:
            return

        self._closed = True
        self._cleanup()
        self._loop.stop()

    def _cleanup(self) -> None:
        """Internal cleanup routine.

        Attempts best-effort cleanup of:
            - all asyncio tasks
            - session fd readers
            - resize watchers and stdin readers
            - session close
            - console raw mode restoration

        Returns:
            None
        """
        if self._loop is None:
            return

        for task in asyncio.all_tasks(self._loop):
            try:
                task._log_destroy_pending = False
            except Exception:
                pass
            task.cancel()

        if self._session_fd is not None:
            try:
                self._loop.remove_reader(self._session_fd)
            except Exception:
                pass
            self._session_fd = None

        try:
            self.console.unwatch_resize(self._loop)
        except Exception:
            pass

        try:
            self.console.remove_input_reader(self._loop)
        except Exception:
            pass

        try:
            self.session.close()
        except Exception:
            pass

        try:
            self.console.exit_raw()
        except Exception:
            pass
