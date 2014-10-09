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
        Retrieve a list from the given object using the given key
        
        @type obj: map
        @param obj: Source object
        
        @type key: string
        @param key: Key to retrieve from obj
        
        @type mandatory: bool
        @param mandatory: If True, throws an exception if the key is not found
        
        @rtype: list
        @return: List retrieved from object
    '''
    return __getTypeChecked(obj, key, [ list ], mandatory)

def getStringChecked(obj, key, mandatory=False):
    '''
        Retrieve a string from the given object using the given key
        
        @type obj: map
        @param obj: Source object
        
        @type key: string
        @param key: Key to retrieve from obj
        
        @type mandatory: bool
        @param mandatory: If True, throws an exception if the key is not found
        
        @rtype: string
        @return: String retrieved from object
    '''
    return __getTypeChecked(obj, key, [ basestring ], mandatory)

def getNumberChecked(obj, key, mandatory=False):
    '''
        Retrieve an integer from the given object using the given key
        
        @type obj: map
        @param obj: Source object
        
        @type key: string
        @param key: Key to retrieve from obj
        
        @type mandatory: bool
        @param mandatory: If True, throws an exception if the key is not found
        
        @rtype: long
        @return: Number retrieved from object
    '''
    return __getTypeChecked(obj, key, [ int, long ], mandatory)

def getObjectOrStringChecked(obj, key, mandatory=False):
    '''
        Retrieve an object or string from the given object using the given key
        
        @type obj: map
        @param obj: Source object
        
        @type key: string
        @param key: Key to retrieve from obj
        
        @type mandatory: bool
        @param mandatory: If True, throws an exception if the key is not found
        
        @rtype: string or dict
        @return: String/Object object retrieved from object
    '''
    return __getTypeChecked(obj, key, [ basestring, dict ], mandatory)

def getNumberOrStringChecked(obj, key, mandatory=False):
    '''
        Retrieve a number or string from the given object using the given key
        
        @type obj: map
        @param obj: Source object
        
        @type key: string
        @param key: Key to retrieve from obj
        
        @type mandatory: bool
        @param mandatory: If True, throws an exception if the key is not found
        
        @rtype: string or number
        @return: String/Number object retrieved from object
    '''
    return __getTypeChecked(obj, key, [ basestring, long, int ], mandatory)

def __getTypeChecked(obj, key, valTypes, mandatory=False):
    if not key in obj:
        if mandatory:
            raise RuntimeError('Expected key "%s" in object' % key)
        return None
    
    val = obj[key]
    
    for valType in valTypes:
        if isinstance(val, valType):
            return val
    
    raise RuntimeError('Expected any of types "%s" for key "%s" but got type %s' % (", ".join([str(i) for i in valTypes]), key, type(val)))