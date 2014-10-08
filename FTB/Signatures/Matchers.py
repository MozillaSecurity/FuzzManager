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