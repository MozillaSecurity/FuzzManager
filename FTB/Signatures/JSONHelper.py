'''
JSONHelper

Various functions around JSON encoding/decoding

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

def getArrayChecked(obj, key, mandatory=False):
    '''
        Return a pattern including all register names that are considered valid
    '''
    if not key in obj:
        if mandatory:
            raise RuntimeError('Expected key "%s" in object' % key)
        return None
    
    arr = obj[key]
    
    if not isinstance(arr, list):
        raise RuntimeError('Expected type "list" for key "%s" but got type %s' % (key, type(arr)))
                           
    return arr
