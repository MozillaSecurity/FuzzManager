#!/usr/bin/env python
# encoding: utf-8
'''
AutoRunner -- Determine the correct runner class (GDB, ASan, etc) for
              the given program, instantiate and return it. 

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

import subprocess

from abc import ABCMeta
from FTB.Signatures.CrashInfo import CrashInfo
import os


class AutoRunner():
    '''
    Abstract base class that provides a method to instantiate the right sub class
    for running the given program and obtaining crash information.
    '''
    __metaclass__ = ABCMeta
    
    def __init__(self, binary, args=None, env=None, cwd=None):
        self.binary = binary
        self.cwd = cwd
        
        self.env = env
        if self.env is None:
            self.env = {}
        
        self.args = args
        if self.args is None:
            self.args = []
            
        assert isinstance(self.env, dict)
        assert isinstance(self.args, list)
        
        # The command that we will run for obtaining crash information
        self.cmdArgs = []
        
        # These will hold our results from running
        self.stdout = None
        self.stderr = None
        self.auxCrashData = None
        
    def getCrashInfo(self, configuration):
        if not self.auxCrashData:
            return None
        
        return CrashInfo.fromRawCrashData(self.stdout, self.stderr, configuration, self.auxCrashData)
        
    @staticmethod
    def fromBinaryArgs(binary, args=None, env=None, cwd=None):
        process = subprocess.Popen(["nm", "-g", binary],
                                   stdin = subprocess.PIPE,
                                   stdout = subprocess.PIPE,
                                   stderr = subprocess.PIPE,
                                   cwd=cwd, env=env
                                   )
        
        (stdout, stderr) = process.communicate()
        
        if stdout.find(" __asan_init") >= 0:
            return ASanRunner(binary, args, env, cwd)
        else:
            return GDBRunner(binary, args, env, cwd)
        
        
class GDBRunner(AutoRunner):
    def __init__(self, binary, args=None, env=None, cwd=None):
        AutoRunner.__init__(self, binary, args, env, cwd)
        
        classPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GDB.py")
        self.gdbArgs = [
                        '--batch',
                        '-ex', 'source %s' % classPath,
                        '-ex', 'run',
                        '-ex', 'set pagination 0',
                        '-ex', 'set backtrace limit 128',
                        '-ex', 'bt',
                        '-ex', 'python printImportantRegisters()',
                        '-ex', 'x/2i $pc',
                        '-ex', 'quit',
                        '--args',
                        ]
        
        self.cmdArgs.append("gdb")
        self.cmdArgs.extend(self.gdbArgs)
        self.cmdArgs.append(self.binary)
        self.cmdArgs.extend(self.args)

    def run(self):
        process = subprocess.Popen(
                                   self.cmdArgs,
                                   stdin = subprocess.PIPE,
                                   stdout = subprocess.PIPE,
                                   stderr = subprocess.PIPE,
                                   cwd=self.cwd, env=self.env
                                   )
        
        (self.stdout, self.stderr) = process.communicate()
        
        # Detect where the GDB trace starts/ends
        traceStart = self.stdout.rfind("Program received signal")
        traceStop = self.stdout.rfind("A debugging session is active")
        
        if traceStart < 0:
            return False
        
        if traceStop < 0:
            traceStop = len(self.stdout)
        
        # Move the trace from stdout to auxCrashData
        self.auxCrashData = self.stdout[traceStart:traceStop]
        self.stdout = self.stdout[:traceStart] + self.stdout[traceStop:]
        
        return True

    
class ASanRunner(AutoRunner):
    def __init__(self, binary, args=None, env=None, cwd=None):
        AutoRunner.__init__(self, binary, args, env, cwd)
        
        self.cmdArgs.append(self.binary)
        self.cmdArgs.extend(self.args)
    
    def run(self):
        process = subprocess.Popen(
                                   self.cmdArgs,
                                   stdin = subprocess.PIPE,
                                   stdout = subprocess.PIPE,
                                   stderr = subprocess.PIPE,
                                   cwd=self.cwd, env=self.env
                                   )
        
        (self.stdout, stderr) = process.communicate()
        
        inTrace = False
        self.auxCrashData = []
        self.stderr = []
        for line in stderr.splitlines():
            if inTrace:
                self.auxCrashData.append(line)
                if line.find("==ABORTING") >= 0:
                    inTrace = False
            elif line.find("==ERROR: AddressSanitizer") >= 0:
                self.auxCrashData.append(line)
                inTrace = True
            else:
                self.stderr.append(line)
                
        # Move the trace from stdout to auxCrashData
        self.auxCrashData = os.linesep.join(self.auxCrashData)
        self.stderr = os.linesep.join(self.stderr)
        
        return True