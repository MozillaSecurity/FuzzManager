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

import re
from FTB.Signatures import JSONHelper

class StringMatch():
    def __init__(self, obj):
        self.isPCRE = False
        
        if isinstance(obj, str) or isinstance(obj, unicode):
            self.value = obj
        else:
            self.value = JSONHelper.getStringChecked(obj, "value", True)
            
            matchType = JSONHelper.getStringChecked(obj, "matchType", False)        
            if matchType != None:
                if matchType.lower() == "contains":
                    pass
                elif matchType.lower() == "pcre":
                    self.isPCRE = True
                    self.value = re.compile(self.value)
                else:
                    raise RuntimeError("Unknown match operator specified: %s" % matchType)

    def matches(self, val):
        if self.isPCRE:
            return self.value.search(val) != None
        else:
            return self.value in val

class NumberMatchType:
    GE, GT, LE, LT = range(4)

class NumberMatch():
    def __init__(self, obj):
        self.matchType = None
        
        if isinstance(obj, str) or isinstance(obj, unicode):
            numberMatchComponents = obj.split(None, 1)
            numIdx = 0
            
            if len(numberMatchComponents) > 1:
                numIdx = 1
                matchType = numberMatchComponents[0]
                
                if matchType == "==":
                    pass
                elif matchType == "<":
                    self.matchType = NumberMatchType.LT
                elif matchType == "<=":
                    self.matchType = NumberMatchType.LE
                elif matchType == ">":
                    self.matchType = NumberMatchType.GT
                elif matchType == ">=":
                    self.matchType = NumberMatchType.GE
                else:
                    raise RuntimeError("Unknown match operator specified: %s" % matchType)
            
            try:
                self.value = long(numberMatchComponents[numIdx], 16)
            except ValueError:
                raise RuntimeError("Invalid number specified: %s" % numberMatchComponents[numIdx])
        elif isinstance(obj, int):
            self.value = obj
        else:
            raise RuntimeError("Invalid type %s in NumberMatch." % type(obj))
    
    def matches(self, value):
        if value == None:
            return False
        
        if self.matchType == NumberMatchType.GE:
            return value >= self.value
        elif self.matchType == NumberMatchType.GT:
            return value > self.value
        elif self.matchType == NumberMatchType.LE:
            return value <= self.value
        elif self.matchType == NumberMatchType.LT:
            return value < self.value
        else:
            return value == self.value
