#!/usr/bin/env python
# encoding: utf-8
'''
GDBRunner -- Run a target program with GDB to get crash information

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
import subprocess
from FTB.Signatures.CrashInfo import CrashInfo

class GDBRunner():
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
        
        self.cmdArgs = []
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
        
        traceStart = self.stdout.rfind("Program received signal")
        traceStop = self.stdout.rfind("A debugging session is active")
        
        if traceStart < 0:
            return False
        
        if traceStop < 0:
            traceStop = len(self.stdout)
        
        self.auxCrashData = self.stdout[traceStart:traceStop]
        return True
    
    def getCrashInfo(self, configuration):
        if not self.auxCrashData:
            return None
        
        return CrashInfo.fromRawCrashData(self.stdout, self.stderr, configuration, self.auxCrashData)