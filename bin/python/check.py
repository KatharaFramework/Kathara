import sys

if sys.version_info >= (3, 0):
    sys.stdout.write("Requires Python 2.x, not Python 3.x\n")
    sys.exit(1)