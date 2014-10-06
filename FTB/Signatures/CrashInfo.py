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
        '''
        Create appropriate CrashInfo instance from raw crash data
        
        @type stdout: List of strings
        @param stdout: List of lines as they appeared on stdout
        @type stderr: List of strings
        @param stderr: List of lines as they appeared on stderr
        @type crashData: List of strings
        @param crashData: Optional crash output (e.g. GDB). If not specified, assumed to be on stderr.
        @type platform: string
        @param platform: Optional platform to match the signature platform attribute
        @type product: string
        @param product: Optional product to match the signature product attribute
        @type os: string
        @param os: Optional OS to match the signature OS attribute
        
        @rtype: CrashInfo
        @return: Crash information object
        '''
        if (crashData == None):
            pass
    
    def createCrashSignature(self, forceCrashAddress=False, forceCrashInstruction=False, numFrames=8):
        pass # TODO: Implement crash signature creation
    
    
class ASanCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, crashData=None, platform=None, product=None, os=None):
        '''
        Private constructor, called by CrashInfo.fromRawCrashData. Do not use directly.
        '''
        self.stdout.extend(stdout)
        self.stderr.extend(stderr)
        self.platform = platform
        self.product = product
        self.os = os
        #TODO: Implement ASan parsing
        # backtrace
        # crashAddress =
        
class GDBCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, crashData=None, platform=None, product=None, os=None):
        '''
        Private constructor, called by CrashInfo.fromRawCrashData. Do not use directly.
        '''
        self.stdout.extend(stdout)
        self.stderr.extend(stderr)
        self.platform = platform
        self.product = product
        self.os = os
        #TODO: Implement GDB parsing
        # backtrace
        # crashAddress =
        # crashInstruction =
        # registers
        
    @staticmethod
    def calculateCrashAddress(crashInstruction, registerMap):
        '''
        Calculate the crash address given the crash instruction and register contents
        
        @type crashInstruction: string
        @param crashInstruction: Crash instruction string as provided by GDB
        @type registerMap: Map from string to long
        @param registerMap: Map of register names to values
        @rtype: long
        @return The calculated crash address
        '''
        #TODO: Port code to calculate crash address from Java.
        pass
        
