import asyncio
from typing import Optional

from .IConsoleAdapter import IConsoleAdapter
from .ITerminalSession import ITerminalSession
from .....utils import exec_by_platform


class TerminalRunner(object):
    __slots__ = ["console", "session", "_loop", "_closed", "_tasks", "_session_fd"]

    def __init__(self, console: IConsoleAdapter, session: ITerminalSession) -> None:
        self.console: IConsoleAdapter = console
        self.session: ITerminalSession = session

        self._loop: Optional[asyncio.AbstractEventLoop] = None

        self._closed: bool = False

        self._tasks: list[asyncio.Task] = []
        self._session_fd: Optional[int] = None

    def start(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self.console.enter_raw()
        self.console.watch_resize(self._loop, self._on_resize)

        self.console.install_input_reader(self._loop, self._on_stdin_bytes, self.close)
        self._start_stdout()

        try:
            self._loop.run_forever()
        finally:
            try:
                self._cleanup()
            finally:
                self._loop.close()

    def _on_resize(self, cols: int, rows: int) -> None:
        if self._closed:
            return

        try:
            self.session.resize(cols, rows)
        except Exception:
            self.close()

    def _on_stdin_bytes(self, data: bytes) -> None:
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
        while not self._closed:
            try:
                data = await self._loop.run_in_executor(None, self.session.read, 4096)
            except Exception:
                self.close()
                return

            if self._closed:
                return

            if not data:
                await asyncio.sleep(0.01)
                continue

            try:
                self.console.write_stdout(data)
            except Exception:
                self.close()
                return

    def _start_stdout(self) -> None:
        def unix():
            self._session_fd = self.session.fileno()
            self._loop.add_reader(self._session_fd, self._on_session_readable)

        def windows():
            self._tasks.append(self._loop.create_task(self._threaded_stdout()))

        exec_by_platform(unix, windows, unix)

    def close(self) -> None:
        if self._closed or self._loop is None:
            return

        self._closed = True
        self._cleanup()
        self._loop.stop()

    def _cleanup(self) -> None:
        if self._loop is None:
            return

        for task in list(asyncio.all_tasks(self._loop)):
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
