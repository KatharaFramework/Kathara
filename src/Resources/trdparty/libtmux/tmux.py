import libtmux
import time
import logging
import random

class TMUX(object):

    __instance = None
    __session = None
    __initial_window = None

    @staticmethod
    def get_instance():
        if TMUX.__instance is None:
            TMUX()
        return TMUX.__instance

    def __init__(self, lab_name):
        if TMUX.__instance is not None:
            raise Exception("This class is a singleton!")
        else:
            TMUX.__instance = self
            self.__initial_window="%008x" % random.getrandbits(32)
            self.session_name="Kathara" if lab_name is None else lab_name
            server = libtmux.Server()
            if not server.has_session(self.session_name):
                server.new_session(self.session_name, window_name=self.__initial_window)
            while not server.has_session(self.session_name):
                time.sleep(1)
            logging.debug("Initialized tmux session %s" % self.session_name)
            TMUX.__session = server.find_where({"session_name":self.session_name})

    def start(self, window_name, start_machine):
        while TMUX.__session is None:
            time.sleep(1)
        window = TMUX.__session.find_where({"window_name": window_name})
        if not window:
            logging.debug("Starting tmux window for %s" % window_name)
            window = TMUX.__session.new_window(window_name=window_name, window_shell=start_machine)
        self.__clean()

    def __clean(self):
        initial_window = TMUX.__session.find_where({"window_name": self.__initial_window})
        if initial_window:
            initial_window.kill_window()

    @staticmethod
    def kill_instance():
        if TMUX.__session:
            TMUX.__session.kill_session()
            TMUX.__session = None
        TMUX.__instance = None
