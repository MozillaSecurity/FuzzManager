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

# Ensure print() compatibility with Python 3
from __future__ import print_function

from abc import ABCMeta, abstractmethod
import re
import sys

class CrashInfo():
    '''
    Abstract base class that provides a method to instantiate the right sub class.
    It also supports generating a CrashSignature based on the stored information.
    '''
    __metaclass__ = ABCMeta
    
    def __init__(self):
        # Store the raw data
        self.rawStdout = []
        self.rawStderr = []
        self.rawCrashData = []
        
        # Store processed data
        self.backtrace = []
        self.registers = {}
        self.crashAddress = None
        self.crashInstruction = None
        
        # Store optional environment information
        self.os = None
        self.product = None
        self.platform = None
    
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
        
        assert stdout == None or isinstance(stdout, list)
        assert stderr == None or isinstance(stderr, list)
        assert crashData ==None or isinstance(crashData, list)
        
        if (crashData == None):
            pass
    
    def createCrashSignature(self, forceCrashAddress=False, forceCrashInstruction=False, numFrames=8):
        pass # TODO: Implement crash signature creation
    
    
class ASanCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, crashData=None, platform=None, product=None, os=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)
        
        if stdout != None:
            self.rawStdout.extend(stdout)
            
        if stderr != None:
            self.rawStderr.extend(stderr)
        
        if crashData != None:
            self.rawCrashData.extend(crashData)
        
        self.platform = platform
        self.product = product
        self.os = os
        
        # If crashData is given, use that to find the ASan trace, otherwise use stderr
        if crashData == None:
            asanOutput = stderr
        else:
            asanOutput = crashData

        # For better readability, list all the formats here, then join them into the regular expression
        asanMessages = [
            "on address", # The most common format, used for all overflows
            "on unknown address", # Used in case of a SIGSEGV
            "double-free on", # Used in case of a double-free
            "not malloc\\(\\)\\-ed:", # Used in case of a wild free (on unallocated memory)
            "not owned:" # Used when calling __asan_get_allocated_size() on a pointer that isn't owned
        ]
        
        # TODO: Support "memory ranges [%p,%p) and [%p, %p) overlap" ?
        
        asanCrashAddressPattern = " AddressSanitizer:.+ (?:" + "|".join(asanMessages) + ")\\s+0x([0-9a-f]+)"
        asanRegisterPattern = "(?:\\s+|\\()pc\\s+0x([0-9a-f]+)\\s+(sp|bp)\\s+0x([0-9a-f]+)\\s+(sp|bp)\\s+0x([0-9a-f]+)"
        
        expectedIndex = 0
        for traceLine in asanOutput:
            if self.crashAddress == None:
                match = re.search(asanCrashAddressPattern, traceLine)
                
                if match != None:
                    self.crashAddress = long(match.group(1), 16)
                
                    # Crash Address and Registers are in the same line for ASan
                    match = re.search(asanRegisterPattern, traceLine)
                    if match != None:
                        self.registers["pc"] = long(match.group(1), 16)
                        self.registers[match.group(2)] = long(match.group(3), 16)
                        self.registers[match.group(4)] = long(match.group(5), 16)
                    else:
                        raise RuntimeError("Fatal error parsing ASan trace: Failed to isolate registers in line: %s" % traceLine)

                    
            parts = traceLine.strip().split()
                        
            # We only want stack frames
            if not parts or not parts[0].startswith("#"):
                continue
            
            index = int(parts[0][1:])
            
            # We may see multiple traces in ASAN
            if index == 0:
                expectedIndex = 0
            
            if not expectedIndex == index:
                raise RuntimeError("Fatal error parsing ASan trace (Index mismatch, got index %s but expected %s)" % (index, expectedIndex) )
            
            component = None
            if len(parts) > 2:
                if parts[2] == "in":
                    component = " ".join(parts[3:-1])
                else:
                    # Remove parentheses around component 
                    component = parts[2][1:-1]
            else:
                print("Warning: Missing component in this line: %s" % traceLine, file=sys.stderr)
                component = "<missing>"
                
            self.backtrace.append(component)
            expectedIndex += 1
        
class GDBCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, crashData=None, platform=None, product=None, os=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)
        
        if stdout != None:
            self.rawStdout.extend(stdout)
            
        if stderr != None:
            self.rawStderr.extend(stderr)
        
        if crashData != None:
            self.rawCrashData.extend(crashData)
            
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
        
