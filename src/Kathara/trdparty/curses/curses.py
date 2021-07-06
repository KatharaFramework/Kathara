import curses


class Curses(object):
    __slots__ = ['_window']

    __instance = None

    @staticmethod
    def get_instance():
        if Curses.__instance is None:
            Curses()

        return Curses.__instance

    def __init__(self):
        if Curses.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self._window = None

            Curses.__instance = self

    def init_window(self, noecho=True, nocbreak=True, timeout=1000, scrollok=True, keypad=True):
        self._window = curses.initscr()
        if noecho:
            curses.noecho()
        if nocbreak:
            curses.nocbreak()
        self._window.timeout(timeout)
        self._window.scrollok(scrollok)
        self._window.keypad(keypad)

    def print_string(self, string, erase=True):
        if not self._window:
            raise Exception("Window not initialized, call init_window first.")

        if erase:
            self._window.erase()

        self._window.addstr(string)
        self._window.refresh()

        key = self._window.getch()
        if key == 3:                                # CTRL+C
            raise KeyboardInterrupt

    def close(self):
        curses.nocbreak()
        self._window.keypad(False)
        curses.echo()
        curses.endwin()

        self._window = None
