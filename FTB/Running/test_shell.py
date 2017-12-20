'''
A simple shell used by tests for persistent application

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

import os
import signal
import sys
import time


def crash():
    import ctypes

    # Causes a NULL deref
    ctypes.string_at(0)


def hang():
    while True:
        time.sleep(1)


def stop():
    os.kill(os.getpid(), signal.SIGSTOP)


def processInput(mode, inputFd):
    received_aa = False

    if mode == "none":
        data = inputFd.read()
        if len(data) == 2:
            sys.exit(0)
        if len(data) == 3:
            sys.exit(1)
        else:
            crash()
    elif mode == "spfp":
        lines = []

        while True:
            line = inputFd.readline()

            if not line:
                break

            line = line.rstrip()
            if line == "spfp-selftest":
                print("SPFP: PASSED")
            elif line == "spfp-endofdata":
                if received_aa and "aaaa" in lines:
                    crash()
                elif "aa" in lines:
                    received_aa = True
                elif "aaaaa" in lines:
                    hang()

                print("SPFP: OK")
            else:
                print(line)
                lines.append(line)
    elif mode == "sigstop":
        while True:
            stop()
            with open(inputFd.name) as inputFd2:
                lines = inputFd2.read().splitlines()

                for line in lines:
                    print(line)
                    print(line, file=sys.stderr)

                if received_aa and "aaaa" in lines:
                    crash()
                elif "aa" in lines:
                    received_aa = True
                elif "aaaaa" in lines:
                    hang()

    elif mode == "faulty_sigstop":
        # And we're gone, how rude
        sys.exit(0)


def main():
    if len(sys.argv) < 2:
        print("Need at least one argument (mode)", file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1]

    print("Stdout test1")
    print("Stderr test1", file=sys.stderr)

    print("Stdout test2")
    print("Stderr test2", file=sys.stderr)

    if len(sys.argv) > 2:
        with open(sys.argv[2]) as inputFd:
            processInput(mode, inputFd)
    else:
        processInput(mode, sys.stdin)

    return 0


if __name__ == "__main__":
    main()
