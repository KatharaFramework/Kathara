def get_terminal_size_windows() -> (int, int):
    try:
        from ctypes import windll, create_string_buffer

        # stdin handle is -10
        # stdout handle is -11
        # stderr handle is -12

        h = windll.kernel32.GetStdHandle(-12)
        csbi = create_string_buffer(22)
        res = windll.kernel32.GetConsoleScreenBufferInfo(h, csbi)

        if res:
            import struct
            (_, _, _, _, _, left, top, right, bottom, _, _) = struct.unpack("hhhhHhhhhhh", csbi.raw)
            w = right - left + 1
            h = bottom - top + 1

            return w, h
    except Exception:
        return get_terminal_size_tput()


def get_terminal_size_tput() -> (int, int):
    try:
        import subprocess
        proc = subprocess.Popen(['tput', 'cols'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output = proc.communicate(input=None)
        w = int(output[0])
        proc = subprocess.Popen(['tput', 'lines'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        output = proc.communicate(input=None)
        h = int(output[0])

        return w, h
    except Exception:
        return 80, 25
