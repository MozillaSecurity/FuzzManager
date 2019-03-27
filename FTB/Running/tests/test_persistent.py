# coding: utf-8
'''
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
from __future__ import print_function
import os
import sys
import time
import pytest

from FTB.Running.PersistentApplication import SimplePersistentApplication, PersistentMode, ApplicationStatus

TEST_PATH = os.path.dirname(__file__)


def test_PersistentApplicationTestModeNone(tmp_path):
    def _check(spa):
        try:
            ret = spa.start("aa")

            assert ret == ApplicationStatus.OK

            assert spa.stdout[0] == "Stdout test1"
            assert spa.stdout[1] == "Stdout test2"

            assert spa.stderr[0] == "Stderr test1"
            assert spa.stderr[1] == "Stderr test2"

            ret = spa.start("aaa")
            assert ret == ApplicationStatus.ERROR

            # Check that stdout/err is reset
            assert len(spa.stdout) == 2
            assert len(spa.stderr) == 2

            # Check that the test log is reset
            assert len(spa.testLog) == 1

            ret = spa.start("aaaa")
            assert ret == ApplicationStatus.CRASHED
        finally:
            spa.stop()

    # Check with stdin as source
    _check(SimplePersistentApplication(sys.executable, [os.path.join(TEST_PATH, "test_shell.py"), "none"]))

    # Now use a temporary file instead
    inputFile = tmp_path / "input.tmp"
    inputFile.touch()
    _check(SimplePersistentApplication(sys.executable, [os.path.join(TEST_PATH, "test_shell.py"), "none",
                                                        str(inputFile)],
                                       inputFile=str(inputFile)))


@pytest.mark.xfail
def test_PersistentApplicationTestOtherModes(tmp_path):
    def _check(spa):
        try:
            ret = spa.start()

            # Start shouldn't return anything in persistent mode
            assert ret is None

            ret = spa.runTest("aaa\naaaa")

            assert ret == ApplicationStatus.OK

            assert spa.stdout[2] == "aaa"
            assert spa.stdout[3] == "aaaa"

            ret = spa.runTest("aa\naaa")

            assert ret == ApplicationStatus.OK

            ret = spa.runTest("aaa\naaaa")
            print(spa.stdout)
            print(spa.stderr)
            assert ret == ApplicationStatus.CRASHED

            assert len(spa.testLog) == 3

            oldPid = spa.process.pid

            spa.stop()
            spa.start()

            newPid = spa.process.pid

            assert oldPid != newPid

            ret = spa.runTest("aaaaa")

            assert ret == ApplicationStatus.TIMEDOUT
            assert len(spa.testLog) == 1
        finally:
            spa.stop()

    # Check with spfp and stdin as source
    _check(SimplePersistentApplication(sys.executable, [os.path.join(TEST_PATH, "test_shell.py"), "spfp"],
                                       persistentMode=PersistentMode.SPFP, processingTimeout=2))

    # Check with sigstop and temporary file as source
    inputFile = tmp_path / "input.tmp"
    inputFile.touch()
    _check(SimplePersistentApplication(sys.executable, [os.path.join(TEST_PATH, "test_shell.py"), "sigstop",
                                                        str(inputFile)],
                                       persistentMode=PersistentMode.SIGSTOP, processingTimeout=2,
                                       inputFile=str(inputFile)))


@pytest.mark.xfail
def test_PersistentApplicationTestPerf(tmp_path):
    def _check(spa):
        try:
            spa.start()

            oldPid = spa.process.pid
            startTime = time.time()

            for i in range(1, 10000):
                spa.runTest("aaa\naaaa")

            stopTime = time.time()
            print("%s execs per second" % (float(10000) / float(stopTime - startTime)))
            newPid = spa.process.pid

            # Make sure we are still in the same process
            assert oldPid == newPid

        finally:
            spa.stop()
    # Check with spfp and stdin as source
    _check(SimplePersistentApplication(sys.executable, [os.path.join(TEST_PATH, "test_shell.py"), "spfp"],
                                       persistentMode=PersistentMode.SPFP, processingTimeout=3))

    # Check with sigstop and temporary file as source
    inputFile = tmp_path / "input.tmp"
    inputFile.touch()
    _check(SimplePersistentApplication(sys.executable, [os.path.join(TEST_PATH, "test_shell.py"), "sigstop",
                                                        str(inputFile)],
                                       persistentMode=PersistentMode.SIGSTOP, processingTimeout=3,
                                       inputFile=str(inputFile)))


def test_PersistentApplicationTestFaultySigstop(tmp_path):
    inputFile = tmp_path / "input.tmp"
    inputFile.touch()
    spa = SimplePersistentApplication(sys.executable, [os.path.join(TEST_PATH, "test_shell.py"), "faulty_sigstop",
                                                       str(inputFile)],
                                      persistentMode=PersistentMode.SIGSTOP, inputFile=str(inputFile))

    with pytest.raises(RuntimeError):
        spa.start()


def test_PersistentApplicationTestStopWithoutStart(tmp_path):
    inputFile = tmp_path / "input.tmp"
    inputFile.touch()
    spa = SimplePersistentApplication(sys.executable, [os.path.join(TEST_PATH, "test_shell.py"), "faulty_sigstop",
                                                       str(inputFile)],
                                      persistentMode=PersistentMode.SIGSTOP, inputFile=str(inputFile))

    # Should not throw, instead it should be a no-op
    spa.stop()
