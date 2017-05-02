import subprocess
import sys

def run_command_detatched(cmd_line):
    process = subprocess.Popen(cmd_line, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # Poll process for new output until finished
    while True:
        nextline = process.stdout.readline()
        if nextline == '' and process.poll() is not None:
            break
        sys.stderr.write(nextline)

    output = process.communicate()[0]
    exitCode = process.returncode

    if (exitCode != 0):
        sys.stderr.write(str(exitCode))
    
    sys.stderr.flush()
    return output