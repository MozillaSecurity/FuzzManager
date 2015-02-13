#!/usr/bin/env python
# encoding: utf-8
'''
PersistentApplication -- Implements a persistent application for performing
multiple tests and offers an interface to perform the necessary tasks around
testing such an application.

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
import subprocess
import os
import Queue
import time
import signal

from FTB.Running.StreamCollector import StreamCollector


class ApplicationStatus:
    OK, ERROR, TIMEDOUT, CRASHED = range(1,5)

class PersistentApplication():
    '''
    Abstract base class that defines the interface
    '''
    __metaclass__ = ABCMeta
    
    def __init__(self, binary, args=None, env=None, cwd=None):
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
        
        # Various variables holding information about the program
        self.process = None
        self.stdout = None
        self.stderr = None
        self.testLog = None
 
    def start(self):
        pass
    
    def stop(self):
        pass
    
    def runTest(self, test):
        pass
    
    def status(self):
        pass
        
class SimplePersistentApplication(PersistentApplication):
    def __init__(self, binary, args=None, env=None, cwd=None):
        PersistentApplication.__init__(self, binary, args, env, cwd)
        
        # How many seconds to give the program for processing out input
        self.processingTimeout = 10
        
    def start(self):
        assert self.process == None or self.process.poll() != None
        
        # Reset the test log
        self.testLog = []
        
        popenArgs = [ self.binary ]
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
        self.responseQueue = Queue.Queue()
        
        self.outCollector = StreamCollector(self.process.stdout, self.responseQueue, logResponses=False, maxBacklog=256)
        self.errCollector = StreamCollector(self.process.stderr, self.responseQueue, logResponses=False, maxBacklog=256)
        
        # Anything prefixed with "SPFP: " will be directly forwarded to us
        self.outCollector.addResponsePrefix("SPFP: ")
        self.errCollector.addResponsePrefix("SPFP: ")
        
        self.outCollector.start()
        self.errCollector.start()
        
        try:
            self.process.stdin.write('selftest\n')
        except IOError:
            raise RuntimeError("SPFP Error: Selftest failed, application did not start properly.")

        try:
            response = self.responseQueue.get(block=True, timeout=self.processingTimeout)
        except Queue.Empty:
            raise RuntimeError("SPFP Error: Selftest failed, no response.")
        
        if response != "PASSED":
            raise RuntimeError("SPFP Error: Selftest failed, unsupported application response: %s" % response)
        
    def stop(self):
        self._terminateProcess()
                
        # Ensure we leave no dangling threads when stopping
        self.outCollector.join()
        self.errCollector.join()
        
        # Make the output available
        self.stdout = self.outCollector.output
        self.stderr = self.errCollector.output
        
    def runTest(self, test):
        if self.process == None or self.process.poll() != None:
            self.start()
        
        self.testLog.append(test)
        self.process.stdin.write('%s\n' % test)

        try:
            response = self.responseQueue.get(block=True, timeout=self.processingTimeout)
        except Queue.Empty:
            if self.process.poll() == None:
                # The process is still running, force it to stop and return timeout code
                self.stop()
                return ApplicationStatus.TIMEDOUT
            else:
                # The process has exited. We need to check if it crashed, but first we
                # call stop to join our collector threads.
                self.stop()
                
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
                            return ApplicationStatus.CRASHED
                    
                    # The application was terminated by a signal, but not by one of the listed signals.
                    # We consider this a fatal error. Either the signal should be supported here, or the
                    # process is being terminated by something else, making the testing unreliable.
                    #
                    # TODO: This could be triggered by the Linux kernel OOM killer
                    raise RuntimeError("SPFP Error: Application terminated with signal: %s" % self.process.returncode)
                else:
                    # The application exited, but didn't send us any message before doing so. We consider this
                    # a protocol violation and raise an exception.
                    raise RuntimeError("SPFP Error: Application exited without message. Exitcode: %s" % self.process.returncode)
        
        if response == 'OK':
            return ApplicationStatus.OK
        elif response == 'ERROR':
            return ApplicationStatus.ERROR
        
        raise RuntimeError("SPFP Error: Unsupported application response: %s" % response)
            
    def _terminateProcess(self):
        if self.process:
            if self.process.poll() == None:
                # Try to terminate the process gracefully first
                self.process.terminate()
                
                # Emulate a wait() with timeout. Because wait() having
                # a timeout would be way too easy, wouldn't it? -.-
                (maxSleepTime, pollInterval) = (3, 0.2)
                while self.process.poll() == None and maxSleepTime > 0:
                    maxSleepTime -= pollInterval
                    time.sleep(pollInterval)
                
                # Process is still alive, kill it and wait
                if self.process.poll() == None:
                    self.process.kill()
                    self.process.wait()
        