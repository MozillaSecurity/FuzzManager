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
        pass
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        return False
    
class StackFrameSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        pass
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        return False

class StackSizeSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        pass
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        return False
    
class CrashAddressSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        pass
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        return False
    
class InstructionSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        pass
    
    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against 
        
        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        return False