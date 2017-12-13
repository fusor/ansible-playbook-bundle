###################################
# Shell
###################################

import subprocess
import os


def execute_cmd(cmd, env=None):
    # print " ".join(cmd)

    run_env = None
    if env:
        run_env = os.environ.copy()
        run_env.update(env)

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=run_env)
    out, err = proc.communicate()
    proc.wait()
    return {
        "returncode": proc.returncode,
        "stdout": out,
        "stderr": err,
    }


def execute_cmd_out(cmd, env=None):
    # print " ".join(cmd)

    run_env = None
    if env:
        run_env = os.environ.copy()
        run_env.update(env)

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=run_env)
    for line in iter(proc.stdout.readline, b''):
        print(">>> " + line.rstrip())

    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
