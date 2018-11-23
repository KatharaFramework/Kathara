import subprocess
import sys

def run_command_detatched(cmd_line):
    cmd_line = cmd_line.encode(sys.getfilesystemencoding())
    if len(cmd_line) > 8192:
        sys.stderr.write("Command line too long, probably because of a long path to this lab. Try moving the lab to a shorter path. The status is now corrupted, please run lclean or lwipe.\n")
        exit(0)
    try:
        process = subprocess.Popen(cmd_line.decode(), shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except:
        process = subprocess.Popen(cmd_line, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # Poll process for new output until finished
    while True:
        nextline = process.stdout.readline().decode('utf-8')
        if nextline == '' and process.poll() is not None:
            break
        sys.stderr.write(nextline)

    output = process.communicate()[0]
    exitCode = process.returncode

    if (exitCode != 0):
        sys.stderr.write(str(exitCode))
    
    sys.stderr.flush()
    return output