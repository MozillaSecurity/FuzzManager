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
        
        classPath = os.path.abspath(__file__)
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
        
        traceStart = self.stderr.rfind("Program received signal")
        traceStop = self.stderr.rfind("A debugging session is active")
        
        if traceStart < 0:
            return False
        
        if traceStop < 0:
            traceStop = len(self.stderr)
        
        self.auxCrashData = self.stderr[traceStart:traceStop]
        return True
    
    def getCrashInfo(self, configuration):
        if not self.auxCrashData:
            return None
        
        return CrashInfo.fromRawCrashData(self.stdout, self.stderr, configuration, self.auxCrashData)

# The following definitions are used by GDB directly when loading this file

def is64bit():
    return not str(gdb.parse_and_eval("$rax"))=="void"

def isARM():
    return not str(gdb.parse_and_eval("$r0"))=="void"

def regAsHexStr(reg):
    if is64bit():
        mask = 0xffffffffffffffff
    else:
        mask = 0xffffffff
    return "0x%x"%(int(str(gdb.parse_and_eval("$" + reg)),0) & mask)

def regAsIntStr(reg):
    return str(int(str(gdb.parse_and_eval("$" + reg)),0))

def regAsRaw(reg):
    return str(gdb.parse_and_eval("$" + reg))

def printImportantRegisters():
    if is64bit(): 
        regs = "rax rbx rcx rdx rsi rdi rbp rsp r8 r9 r10 r11 r12 r13 r14 r15 rip".split(" ")
    elif isARM():
        regs = "r0 r1 r2 r3 r4 r5 r6 r7 r8 r9 r10 r11 r12 sp lr pc cpsr".split(" ")
    else:
        regs = "eax ebx ecx edx esi edi ebp esp eip".split(" ")

    for reg in regs:
        try:
            print(reg + "\t" + regAsHexStr(reg) + "\t" + regAsIntStr(reg))
        except:
            print(reg + "\t" + regAsRaw(reg))