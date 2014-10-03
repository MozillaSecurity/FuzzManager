'''
AssertionHelper

Provides various functions around assertion handling and processing

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

def getAssertion(output, onlyProgramAssertions=False):
    '''
    This helper class provides a way to extract and process the 
    different types of assertions from a given buffer. 
    The problem here is that pretty much every software has its 
    own type of assertions with different output formats.
    
    The "onlyProgramAssertions" boolean is to indicate that we
    are only interested in output from the program itself.
    Some aborts, like ASan or glibc, are not desirable in some
    cases, like signature generation and lead to incompatible
    signatures.
     
    :param output: List of strings to be searched
    :param onlyProgramAssertions: Boolean, see above
    '''
    #TODO: Implement/Port assertion extraction code
    pass

def getSanitizedAssertionPattern(msg):
    '''
    This method provides a way to strip out unwanted dynamic information 
    from assertions and replace it with pattern matching elements, e.g. 
    for use in signature matching.
    
    :param msg: Assertion message to be sanitized
    '''
    #TODO: Implement/Port assertion sanitizing code
    pass
    
def escapePattern(msg):
    '''
    This method escapes regular expression characters in the string.
    And no, this is not Pattern.quote, which wouldn't work in this
    case.
    
    :param msg: String that needs to be quoted
    '''
    #TODO: Implement/Port escapePattern code
    pass