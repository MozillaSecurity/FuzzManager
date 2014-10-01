'''
Crash Information

Represents information about a crash. Specific subclasses implement
different crash data supported by the implementation.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

from abc import ABCMeta, abstractmethod

class CrashInfo():
    '''
    Abstract base class that provides a method to instantiate the right sub class.
    It also supports generating a CrashSignature based on the stored information.
    '''
    __metaclass__ = ABCMeta
    
    backtrace = []
    stdout = []
    stderr = []
    registers = {}
    crashAddress = None
    crashInstruction = None
    os = None
    product = None
    platform = None
    
    @staticmethod
    def fromRawCrashData(stdout, stderr, crashData=None, platform=None, product=None, os=None):
        if (crashData == None):
            pass
    
    def createCrashSignature(self, forceCrashAddress=False, forceCrashInstruction=False, numFrames=8):
        pass # TODO: Implement
    
    
class ASanCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, crashData=None, platform=None, product=None, os=None):
        self.stdout.extend(stdout)
        self.stderr.extend(stderr)
        self.platform = platform
        self.product = product
        self.os = os
        #TODO: Implement ASan parsing here
        # backtrace
        # crashAddress =
        
class GDBCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, crashData=None, platform=None, product=None, os=None):
        self.stdout.extend(stdout)
        self.stderr.extend(stderr)
        self.platform = platform
        self.product = product
        self.os = os
        #TODO: Implement GDB parsing here
        # backtrace
        # crashAddress =
        # crashInstruction =
        # registers
        
    @staticmethod
    def calculateCrashAddress(crashInstruction, registerMap):
        #TODO: Port this code from Java. It's complicated ^.^
        pass
        
