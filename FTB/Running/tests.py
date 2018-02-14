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
import tempfile
import time
import unittest

from FTB.Running.PersistentApplication import SimplePersistentApplication, PersistentMode, ApplicationStatus

TEST_PATH = os.path.dirname(__file__)


class PersistentApplicationTestModeNone(unittest.TestCase):
    def runTest(self):
        def _check(spa):
            ret = spa.start("aa")

            self.assertEqual(ret, ApplicationStatus.OK)

            self.assertEqual(spa.stdout[0], "Stdout test1")
            self.assertEqual(spa.stdout[1], "Stdout test2")

            self.assertEqual(spa.stderr[0], "Stderr test1")
            self.assertEqual(spa.stderr[1], "Stderr test2")

            ret = spa.start("aaa")
            self.assertEqual(ret, ApplicationStatus.ERROR)

            # Check that stdout/err is reset
            self.assertEqual(len(spa.stdout), 2)
            self.assertEqual(len(spa.stderr), 2)

            # Check that the test log is reset
            self.assertEqual(len(spa.testLog), 1)

            ret = spa.start("aaaa")
            self.assertEqual(ret, ApplicationStatus.CRASHED)

        # Check with stdin as source
        _check(SimplePersistentApplication("python", [os.path.join(TEST_PATH, "test_shell.py"), "none"]))

        # Now use a temporary file instead
        (_, inputFile) = tempfile.mkstemp()
        _check(SimplePersistentApplication("python", [os.path.join(TEST_PATH, "test_shell.py"), "none", inputFile],
                                           inputFile=inputFile))
        os.remove(inputFile)


class PersistentApplicationTestOtherModes(unittest.TestCase):
    def runTest(self):
        def _check(spa):
            ret = spa.start()

            # Start shouldn't return anything in persistent mode
            self.assertEqual(ret, None)

            ret = spa.runTest("aaa\naaaa")

            self.assertEqual(ret, ApplicationStatus.OK)

            self.assertEqual(spa.stdout[2], "aaa")
            self.assertEqual(spa.stdout[3], "aaaa")

            ret = spa.runTest("aa\naaa")

            self.assertEqual(ret, ApplicationStatus.OK)

            ret = spa.runTest("aaa\naaaa")
            print(spa.stdout)
            print(spa.stderr)
            self.assertEqual(ret, ApplicationStatus.CRASHED)

            self.assertEqual(len(spa.testLog), 3)

            oldPid = spa.process.pid

            spa.stop()
            spa.start()

            newPid = spa.process.pid

            self.assertNotEqual(oldPid, newPid)

            ret = spa.runTest("aaaaa")

            self.assertEqual(ret, ApplicationStatus.TIMEDOUT)
            self.assertEqual(len(spa.testLog), 1)

        # Check with spfp and stdin as source
        _check(SimplePersistentApplication("python", [os.path.join(TEST_PATH, "test_shell.py"), "spfp"],
                                           persistentMode=PersistentMode.SPFP, processingTimeout=2))

        # Check with sigstop and temporary file as source
        (_, inputFile) = tempfile.mkstemp()
        _check(SimplePersistentApplication("python", [os.path.join(TEST_PATH, "test_shell.py"), "sigstop", inputFile],
                                           persistentMode=PersistentMode.SIGSTOP, processingTimeout=2,
                                           inputFile=inputFile))
        os.remove(inputFile)


class PersistentApplicationTestPerf(unittest.TestCase):
    def runTest(self):
        def _check(spa):
            spa.start()

            oldPid = spa.process.pid
            startTime = time.time()

            for i in range(1, 10000):
                spa.runTest("aaa\naaaa")

            stopTime = time.time()
            print("%s execs per second" % (float(10000) / float(stopTime - startTime)))
            newPid = spa.process.pid

            # Make sure we are still in the same process
            self.assertEqual(oldPid, newPid)

            spa.stop()
        # Check with spfp and stdin as source
        _check(SimplePersistentApplication("python", [os.path.join(TEST_PATH, "test_shell.py"), "spfp"],
                                           persistentMode=PersistentMode.SPFP, processingTimeout=3))

        # Check with sigstop and temporary file as source
        (_, inputFile) = tempfile.mkstemp()
        _check(SimplePersistentApplication("python", [os.path.join(TEST_PATH, "test_shell.py"), "sigstop", inputFile],
                                           persistentMode=PersistentMode.SIGSTOP, processingTimeout=3,
                                           inputFile=inputFile))
        os.remove(inputFile)


class PersistentApplicationTestFaultySigstop(unittest.TestCase):
    def runTest(self):
        (_, inputFile) = tempfile.mkstemp()
        spa = SimplePersistentApplication("python", [os.path.join(TEST_PATH, "test_shell.py"), "faulty_sigstop",
                                                     inputFile],
                                          persistentMode=PersistentMode.SIGSTOP, inputFile=inputFile)

        with self.assertRaises(RuntimeError):
            spa.start()

        os.remove(inputFile)


class PersistentApplicationTestStopWithoutStart(unittest.TestCase):
    def runTest(self):
        (_, inputFile) = tempfile.mkstemp()
        spa = SimplePersistentApplication("python", [os.path.join(TEST_PATH, "test_shell.py"), "faulty_sigstop",
                                                     inputFile],
                                          persistentMode=PersistentMode.SIGSTOP, inputFile=inputFile)

        # Should not throw, instead it should be a no-op
        spa.stop()
        os.remove(inputFile)


if __name__ == "__main__":
    unittest.main()
