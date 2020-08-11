import logging
import random

import libtmux


class TMUX(object):
    __slots__ = ['_sessions', '_server']

    __instance = None

    @staticmethod
    def get_instance():
        if TMUX.__instance is None:
            TMUX()

        return TMUX.__instance

    def __init__(self):
        if TMUX.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            self._sessions = {}
            self._server = libtmux.Server()

            TMUX.__instance = self

    def add_window(self, session_name, machine_name, shell, cwd=None):
        session_name = "Kathara" if not session_name else session_name

        initial_window_name = "%008x" % random.getrandbits(32)
        session, added = self.add_session(session_name, initial_window_name)

        machine_window = session.find_where({"window_name": machine_name})
        if not machine_window:
            logging.debug("Starting TMUX window for `%s`..." % machine_name)
            session.new_window(window_name=machine_name, window_shell=shell, start_directory=cwd)

        if added:
            self.kill_window(session, initial_window_name)

    def add_session(self, session_name, window_name):
        try:
            self._server.new_session(session_name, window_name=window_name)
        except libtmux.server.exc.TmuxSessionExists:
            session = self._get_session_from_server(session_name)
            self.add_session_by_name(session_name, session)
            return session, False
        except libtmux.server.exc.LibTmuxException as e:
            if 'duplicate session' in e.args[0][0]:
                session = self._get_session_from_server(session_name)
                self.add_session_by_name(session_name, session)
                return session, False

        logging.debug("Initialized TMUX session %s" % session_name)

        session = self._server.find_where({"session_name": session_name})
        self.add_session_by_name(session_name, session)

        return session, True

    def add_session_by_name(self, session_name, session):
        if session_name not in self._sessions:
            self._sessions[session_name] = session

    def get_session_by_name(self, session_name):
        if session_name in self._sessions:
            return self._sessions[session_name]

        return None

    def _get_session_from_server(self, session_name):
        if self._server.has_session(session_name):
            return self._server.find_where({"session_name": session_name})

        return None

    @staticmethod
    def kill_window(session, window_name):
        window = session.find_where({"window_name": window_name})

        if window:
            window.kill_window()
