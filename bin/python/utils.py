import base64
import hashlib
import re
import os
import functools
import datetime
try:
    import pwd
except ImportError: #windows
    pass
import sys
from sys import platform as _platform

non_ascii = r'[^\x00-\x7F]+'

def generate_urlsafe_hash(string):
    string = re.sub(non_ascii,'', string)
    return base64.urlsafe_b64encode(hashlib.md5(string.encode('utf-8', errors='ignore')).digest())[:-2]

# helper functions for natural sorting
def atoi(text):
    return int(text) if text.isdigit() else text
def natural_keys(text):
    return [ atoi(c) for c in re.split('(\d+)', text) ]

def replace_multiple_items(repls, string):
        return functools.reduce(lambda a, kv: a.replace(*kv), repls, string)

# writes the temporary files in NETKIT_HOME/temp
def write_temp(text, filename, mode="linux", file_mode="a+"):
    if mode=="win32":
        out_file = open(os.path.join(os.environ["NETKIT_HOME"], "temp/" + filename), file_mode)
    else:
        out_file = open(os.path.join(pwd.getpwuid(os.getuid()).pw_dir, "netkit_temp/" + filename), file_mode)
    out_file.write(text)
    out_file.close()

def check_folder_or_file_name_in_dir(some_dir, file_or_folder_name):
    for dname, dirs, files in os.walk(some_dir):
        for directory_name in dirs:
            if (file_or_folder_name in directory_name): 
                return True
        for filename in files:
            if (file_or_folder_name in filename): 
                return True

def couple_list_to_dict(clist):
    dic = {}
    for (value, key) in clist:
        dic[str(key)] = value
    return dic

def merge_two_dicts(x, y):
    z = x.copy()
    z.update(y)
    return z

def timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def log(message, mode='a+'):
    filepath=os.path.join(os.environ['NETKIT_HOME'], '..', 'logs.txt')
    if _platform != "win32":
        filepath=os.path.join(os.environ['HOME'], 'kathara_logs.txt')
    with open(filepath, mode) as file:
        file.write(timestamp()  + ' ' + message + '\n')

# A function that takes an integer in the 8-bit range and returns
# a single-character byte object in py3 / a single-character string
# in py2.
#
PY3 = sys.version_info[0] == 3
int2byte = (lambda x: bytes((x,))) if PY3 else chr
_text_characters = (
        b''.join(int2byte(i) for i in range(32, 127)) +
        b'\n\r\t\f\b')

def istextfile(fileobj, blocksize=512):
    """ Uses heuristics to guess whether the given file is text or binary,
        by reading a single block of bytes from the file.
        If more than 30% of the chars in the block are non-text, or there
        are NUL ('\x00') bytes in the block, assume this is a binary file.
    """
    block = fileobj.read(blocksize)
    if b'\x00' in block:
        # Files with null bytes are binary
        return False
    elif not block:
        # An empty file is considered a valid text file
        return True

    # Use translate's 'deletechars' argument to efficiently remove all
    # occurrences of _text_characters from the block
    nontext = block.translate(None, _text_characters)
    return float(len(nontext)) / len(block) <= 0.30