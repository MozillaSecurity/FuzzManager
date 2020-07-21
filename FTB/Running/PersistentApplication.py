# encoding: utf-8
'''
PersistentApplication -- Defines an interface for running multiple tests in
a single target application process (persistent testing). Also includes an
implementation that should work with simple programs. Supports multiple
ways to implement persistent testing.

Note: All of the code here is work in progress. A harness utilizing this
code with a FuzzManager connection will be added soon.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

from abc import ABCMeta
import os
import signal
import subprocess
import time

import six
from six.moves import queue

from FTB.Running.StreamCollector import StreamCollector
from FTB.Running.WaitpidMonitor import WaitpidMonitor


class ApplicationStatus:
    OK, ERROR, TIMEDOUT, CRASHED = range(1, 5)


class PersistentMode:
    """
    Persistent fuzzing mode - determines how the program synchronizes the
    execution of multiple testcases in one process.

    NONE - No persistence at all, program is supposed to exit after every test.

    SPFP - Use the Simple Persistent Fuzzing Protocol (SPFP) to synchronize
           execution. This is a simple message exchange on stdin/stdout/stderr.

           The program must stick to the following rules:

           Listen on stdin for "spfp-selftest" and respond with "SPFP: PASSED".
           Consider everything else on stdin to be test data, terminated by
           "spfp-endofdata". The program must then respond with "SPFP: OK" or
           "SPFP: ERROR" *after* processing the data (i.e. once it is ready to
           receive new data). The program is also not supposed to quit without
           emitting an "SPFP: QUIT" message before.

    SIGSTOP - Use a SIGSTOP-based protocol like AFL implements it. After startup,
              the program is supposed to SIGSTOP itself to indicate that it is
              ready to process data. It should also SIGSTOP itself after each
              successful data processing. This protocol type can also be used
              if no synchronization via stdin is possible
    """
    NONE, SPFP, SIGSTOP = range(1, 4)


@six.add_metaclass(ABCMeta)
class PersistentApplication():
    '''
    Abstract base class that defines the interface
    '''
    def __init__(self, binary, args=None, env=None, cwd=None, persistentMode=PersistentMode.NONE,
                 processingTimeout=10, inputFile=None):
        self.binary = binary
        self.cwd = cwd

        # Use the system environment as a base environment
        self.env = dict(os.environ)
        if env:
            for envkey in env:
                self.env[envkey] = env[envkey]

        self.args = args
        if self.args is None:
            self.args = []

        assert isinstance(self.env, dict)
        assert isinstance(self.args, list)

        # Mode for running persistently
        self.persistentMode = persistentMode

        # How many seconds to give the program for processing out input
        self.processingTimeout = processingTimeout

        # File to write test data to (if empty or None, stdin is used)
        self.inputFile = inputFile

        # Various variables holding information about the program
        self.process = None
        self.stdout = None
        self.stderr = None
        self.testLog = None

        # This string will be used to prefix spfp inputs and can be set
        # to e.g. a comment string prefix for the target input ('//')
        # which can be helpful to make the reply log a valid program
        # in itself.
        self.spfpPrefix = ""
        self.spfpSuffix = ""  # To support <!-- -->

    def start(self, test=None):
        pass

    def stop(self):
        pass

    def runTest(self, test):
        pass

    def status(self):
        pass

    def _crashed(self):
        if self.process.returncode < 0:
            crashSignals = [
                # POSIX.1-1990 signals
                signal.SIGILL,
                signal.SIGABRT,
                signal.SIGFPE,
                signal.SIGSEGV,
                # SUSv2 / POSIX.1-2001 signals
                signal.SIGBUS,
                signal.SIGSYS,
                signal.SIGTRAP,
            ]

            for crashSignal in crashSignals:
                if self.process.returncode == -crashSignal:
                    return True

        return False


class SimplePersistentApplication(PersistentApplication):
    def __init__(self, binary, args=None, env=None, cwd=None, persistentMode=PersistentMode.NONE,
                 processingTimeout=10, inputFile=None):
        PersistentApplication.__init__(self, binary, args, env, cwd, persistentMode,
                                       processingTimeout, inputFile)

        # Used to store the second return value if waitpid, which has the real exit code
        self.childExit = None

        # These will hold our StreamCollectors for stdout/err
        self.outCollector = None
        self.errCollector = None

    def _write_log_test(self, test):
        self.testLog.append(test)

        if self.inputFile:
            with open(self.inputFile, 'w') as inputFileFd:
                inputFileFd.write(test)
        elif self.persistentMode == PersistentMode.SPFP:
            # This won't work with pure binary data, but SPFP mode isn't suitable for that in general
            print(test, file=self.process.stdin)
            print("%sspfp-endofdata%s" % (self.spfpPrefix, self.spfpSuffix), file=self.process.stdin)
        elif self.persistentMode == PersistentMode.SIGSTOP:
            # Shameless copycat, oh hai lcamtuf ;)
            os.ftruncate(self.process.stdin, len(test))
            os.lseek(self.process.stdin, 0, os.SEEK_SET)
            self.process.stdin.write(test)
            self.process.stdin.flush()
        else:
            self.process.stdin.write(test)
            self.process.stdin.close()

    def _wait_child_stopped(self):
        monitor = WaitpidMonitor(self.process.pid, os.WUNTRACED)
        monitor.start()
        monitor.join(self.processingTimeout)

        if monitor.is_alive():
            # Timed out
            return False

        # Save the exit result returned by waitpid() as we need it
        # in case the process crashed or otherwise exited unexpectedly
        self.childExit = monitor.childExit

        return True

    def start(self, test=None):
        assert self.process is None or self.process.poll() is not None

        # Reset the test log
        self.testLog = []

        if self.persistentMode == PersistentMode.NONE:
            assert test is not None
            if self.inputFile:
                self._write_log_test(test)
        else:
            # We should only get a test here if we don't run in persistent mode
            # at all. Otherwise, all tests should go through the runTest method.
            assert test is None

        popenArgs = [self.binary]
        popenArgs.extend(self.args)

        self.process = subprocess.Popen(
            popenArgs,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
            env=self.env,
            universal_newlines=True
        )

        # This queue is used to queue up responses that should be directly processed
        # by this class rather than being logged.
        self.responseQueue = queue.Queue()

        self.outCollector = StreamCollector(self.process.stdout, self.responseQueue, logResponses=False, maxBacklog=256)
        self.errCollector = StreamCollector(self.process.stderr, self.responseQueue, logResponses=False, maxBacklog=256)

        # Anything prefixed with "SPFP: " will be directly forwarded to us.
        # This is helpful for debugging, even with other PersistentMode settings.
        self.outCollector.addResponsePrefix("SPFP: ")
        self.errCollector.addResponsePrefix("SPFP: ")

        self.outCollector.start()
        self.errCollector.start()

        if self.persistentMode == PersistentMode.SPFP:
            try:
                print("%sspfp-selftest%s" % (self.spfpPrefix, self.spfpSuffix), file=self.process.stdin)
            except IOError:
                raise RuntimeError("SPFP Error: Selftest failed, application did not start properly.")

            try:
                response = self.responseQueue.get(block=True, timeout=self.processingTimeout)
            except queue.Empty:
                raise RuntimeError("SPFP Error: Selftest failed, no response.")

            if response != "PASSED":
                raise RuntimeError("SPFP Error: Selftest failed, unsupported application response: %s" % response)
        elif self.persistentMode == PersistentMode.SIGSTOP:
            if not self._wait_child_stopped():
                raise RuntimeError("SIGSTOP Error: Failed to wait for application to stop itself after startup")

            if self.process.poll() is not None:
                raise RuntimeError("SIGSTOP Error: Application terminated instead of stopping itself")
        else:
            if not self.inputFile:
                self._write_log_test(test)

            # Assume PersistentMode.NONE and expect the process to exit now
            (maxSleepTime, pollInterval) = (self.processingTimeout, 0.2)
            while self.process.poll() is None and maxSleepTime > 0:
                maxSleepTime -= pollInterval
                time.sleep(pollInterval)

            ret = ApplicationStatus.OK

            # Process is still alive, consider this a timeout
            if self.process.poll() is None:
                ret = ApplicationStatus.TIMEDOUT
            elif self._crashed():
                ret = ApplicationStatus.CRASHED
            elif self.process.returncode:
                ret = ApplicationStatus.ERROR

            # Stop threads, make output available.
            # Also terminates the process in case of a timeout.
            self.stop()

            return ret

    def stop(self):
        self._terminateProcess()

        # Ensure we leave no dangling threads when stopping
        if self.outCollector is not None:
            # errCollector is expected to be set when outCollector is
            self.outCollector.join()
            self.errCollector.join()

            # Make the output available
            self.stdout = self.outCollector.output
            self.stderr = self.errCollector.output

    def runTest(self, test):
        if self.process is None or self.process.poll() is not None:
            self.start()

        # Write test data and also log it
        self._write_log_test(test)

        if self.persistentMode == PersistentMode.SPFP:
            try:
                response = self.responseQueue.get(block=True, timeout=self.processingTimeout)
            except queue.Empty:
                if self.process.poll() is None:
                    # The process is still running, force it to stop and return timeout code
                    self.stop()
                    return ApplicationStatus.TIMEDOUT
                else:
                    # The process has exited. We need to check if it crashed, but first we
                    # call stop to join our collector threads.
                    self.stop()

                    if self._crashed():
                        return ApplicationStatus.CRASHED
                    elif self.process.returncode < 0:
                        # The application was terminated by a signal, but not by one of the listed signals.
                        # We consider this a fatal error. Either the signal should be supported here, or the
                        # process is being terminated by something else, making the testing unreliable.
                        #
                        # TODO: This could be triggered by the Linux kernel OOM killer
                        raise RuntimeError("SPFP Error: Application terminated with signal: %s" %
                                           self.process.returncode)
                    else:
                        # The application exited, but didn't send us any message before doing so. We consider this
                        # a protocol violation and raise an exception.
                        raise RuntimeError("SPFP Error: Application exited without message. Exitcode: %s" %
                                           self.process.returncode)

            # Update stdout/err available for the last run
            self.stdout = self.outCollector.output
            self.stderr = self.errCollector.output

            if response == 'OK':
                return ApplicationStatus.OK
            elif response == 'ERROR':
                return ApplicationStatus.ERROR

            raise RuntimeError("SPFP Error: Unsupported application response: %s" % response)
        elif self.persistentMode == PersistentMode.SIGSTOP:
            # Resume the process
            os.kill(self.process.pid, signal.SIGCONT)

            # Wait for process to stop itself again
            if not self._wait_child_stopped():
                # The process is still running, force it to stop and return timeout code
                self.stop()
                return ApplicationStatus.TIMEDOUT

            # Update stdout/err available for the last run
            self.stdout = self.outCollector.output
            self.stderr = self.errCollector.output

            if self.process.poll() is not None:
                exitCode = self.childExit >> 8
                signalNum = self.childExit & 0xFF

                if exitCode:
                    self.process.returncode = exitCode
                else:
                    self.process.returncode = -signalNum

                if self._crashed():
                    return ApplicationStatus.CRASHED
                else:
                    return ApplicationStatus.ERROR

            return ApplicationStatus.OK

    def _terminateProcess(self):
        if self.process:
            if self.process.poll() is None:
                # Try to terminate the process gracefully first
                self.process.terminate()

                # Emulate a wait() with timeout. Because wait() having
                # a timeout would be way too easy, wouldn't it? -.-
                (maxSleepTime, pollInterval) = (3, 0.2)
                while self.process.poll() is None and maxSleepTime > 0:
                    maxSleepTime -= pollInterval
                    time.sleep(pollInterval)

                # Process is still alive, kill it and wait
                if self.process.poll() is None:
                    self.process.kill()
                    self.process.wait()
