'''
Symptom

Represents one symptom which may appear in a crash signature.

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
from FTB.Signatures import JSONHelper
from FTB.Signatures.Matchers import StringMatch, NumberMatch

class Symptom():
    '''
    Abstract base class that provides a method to instantiate the right sub class.
    It also supports generating a CrashSignature based on the stored information.
    '''
    __metaclass__ = ABCMeta
    
    @staticmethod
    def fromJSONObject(obj):
        '''
        Create the appropriate Symptom based on the given object (decoded from JSON)
        
        @type obj: map
        @param obj: Object as decoded from JSON
        
        @rtype: Symptom
        @return: Symptom subclass instance matching the given object
        '''
        if not "type" in obj:
            raise RuntimeError("Missing symptom type in object")
        
        stype = obj["type"]
        
        if (stype == "output"):
            return OutputSymptom(obj)
        elif (stype == "stackFrame"):
            return StackFrameSymptom(obj)
        elif (stype == "stackSize"):
            return StackSizeSymptom(obj)
        elif (stype == "crashAddress"):
            return CrashAddressSymptom(obj)
        elif (stype == "instruction"):
            return InstructionSymptom(obj)
        else:
            raise RuntimeError("Unknown symptom type: %s" % type)

    @abstractmethod
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        return
    
    
class OutputSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        self.output = StringMatch(JSONHelper.getObjectOrStringChecked(obj, "value", True))
        self.src = JSONHelper.getStringChecked(obj, "src")
        
        if self.src != None:
            self.src = self.src.lower()
            if self.src != "stderr" and self.src != "stdout":
                raise RuntimeError("Invalid source specified: %s" % self.src)
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        checkedOutput = []
        
        if self.src == None:
            checkedOutput.extend(crashInfo.rawStdout)
            checkedOutput.extend(crashInfo.rawStderr)
        elif (self.src == "stdout"):
            checkedOutput = crashInfo.rawStdout
        else:
            checkedOutput = crashInfo.rawStderr
            
        for line in checkedOutput:
            if self.output.matches(line):
                return True
            
        return False
    
class StackFrameSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        self.functionName = StringMatch(JSONHelper.getNumberOrStringChecked(obj, "functionName", True))        
        self.frameNumber = JSONHelper.getNumberOrStringChecked(obj, "frameNumber")

        if self.frameNumber != None:
            self.frameNumber = NumberMatch(self.frameNumber)
        else:
            # Default to 0
            self.frameNumber = NumberMatch(0)
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        
        for idx in range(len(crashInfo.backtrace)):
            # Not the most efficient way for very long stacks with a small match area
            if self.frameNumber.matches(idx):
                if self.functionName.matches(crashInfo.backtrace[idx]):
                    return True
        
        return False

class StackSizeSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        self.stackSize = NumberMatch(JSONHelper.getNumberOrStringChecked(obj, "size", True))
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        return self.stackSize.matches(len(crashInfo.backtrace))
    
class CrashAddressSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        self.address = NumberMatch(JSONHelper.getNumberOrStringChecked(obj, "address", True))
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        # In case the crash address is not available,
        # the NumberMatch class will return false to not match.
        return self.address.matches(crashInfo.crashAddress)
    
class InstructionSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        
        self.registerNames = JSONHelper.getArrayChecked(obj, "registerNames")
        self.instructionName = JSONHelper.getObjectOrStringChecked(obj, "instructionName")
        
        if self.instructionName != None:
            self.instructionName = StringMatch(self.instructionName)
        elif self.registerNames == None or len(self.registerNames) == 0:
            raise RuntimeError("Must provide at least instruction name or register names")
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        if crashInfo.crashInstruction == None:
            # No crash instruction available, do not match
            return False
        
        if self.registerNames != None:
            for register in self.registerNames:
                if not register in crashInfo.crashInstruction:
                    return False
        
        if self.instructionName != None:
            if not self.instructionName.matches(crashInfo.crashInstruction):
                return False
        
        return True