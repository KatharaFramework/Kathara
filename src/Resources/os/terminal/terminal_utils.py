import os


def get_terminal_size_windows():
    res = None
    try:
        from ctypes import windll, create_string_buffer

        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12

        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)
    except:
        return None

    if res:
        import struct
        (_, _, _, _, _, left, top, right, bottom, _, _) = struct.unpack("hhhhHhhhhhh", csbi.raw)
        w = right - left + 1
        h = bottom - top + 1

        return w, h
    else:
        return get_terminal_size_tput()


def get_terminal_size_tput():
    try:
        import subprocess
        proc = subprocess.Popen(['tput', 'cols'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output = proc.communicate(input=None)
        w = int(output[0])
        proc = subprocess.Popen(['tput', 'lines'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output = proc.communicate(input=None)
        h = int(output[0])

        return w, h
    except:
        return None


def get_terminal_size_linux():  # pragma: no cover
    try:
        # This works for Python 3, but not Pypy3. Probably the best method if
        # it's supported so let's always try
        import shutil
        h, w = shutil.get_terminal_size((0, 0))
        if h and w:
            return w, h
    except:
        pass

    def ioctl_GWINSZ(fd):
        try:
            import fcntl
            import termios
            import struct
            size = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ, '1234'))
        except:
            return None
        return size

    size = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)

    if not size:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            size = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not size:
        try:
            size = os.environ['LINES'], os.environ['COLUMNS']
        except:
            return None

    return int(size[1]), int(size[0])
