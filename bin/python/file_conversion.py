import os
import re

def win2linux(filename):
    c = open(filename).read()
    c = c[1:] if len(c) > 0 and ord(c[0]) == 0xfeff else c
    open(filename, 'w').write(re.sub(r'\r', '', c))

def win2linux_all_files_in_dir(some_dir):
    for dname, dirs, files in os.walk(some_dir):
        for fname in files:
            fpath = os.path.join(dname, fname)
            win2linux(fpath)