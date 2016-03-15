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

import re


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

    @type output: list
    @param output: List of strings to be searched

    @type onlyProgramAssertions: bool
    @param onlyProgramAssertions: Boolean, see above
    '''
    lastLine = None
    addNext = False

    # Use this to ignore the ASan head line in case of an assertion
    haveFatalAssertion = False

    for line in output:
        # Remove any PID output at the beginning of the line
        line = re.sub("^\\[\\d+\\]\\s+", "", line, count=1)

        if addNext:
            lastLine.append(line)
            addNext = False
        elif line.startswith("Assertion failure"):
            # Firefox fatal assertion (MOZ_ASSERT, JS_ASSERT)
            lastLine = line
            haveFatalAssertion = True
        elif line.startswith("# Fatal error in"):
            # Support v8 non-standard multi-line assertion output
            # We need to return this as array so we can create two
            # symptoms for it as the matchers work by line.
            lastLine = [ line ]
            haveFatalAssertion = True
            addNext = True
        elif not onlyProgramAssertions and not haveFatalAssertion and "ERROR: AddressSanitizer" in line:
            lastLine = line
        elif "Assertion" in line and "failed" in line:
            # Firefox ANGLE assertion
            lastLine = line
        elif ": failed assertion" in line:
            # Firefox Skia assertion (SkASSERT)
            lastLine = line
            haveFatalAssertion = True
        elif not onlyProgramAssertions and "glibc detected" in line:
            # Aborts caused by glibc runtime error detection
            lastLine = line
        elif "MOZ_CRASH" in line and re.search("Hit MOZ_CRASH\(.+\)", line):
            # MOZ_CRASH line, but with a message (we should only look at these)
            lastLine = line
        elif "runtime error" in line and re.search(":\\d+:\\d+: runtime error: ", line):
            # UBSan error. Even though this is not a program assertion, we should
            # really include it in the signature because what UBSan reports here
            # is not really a crash.
            lastLine = line
        elif line.startswith("[Non-crash bug] "):
            # Magic string "added" to stderr by some fuzzers.
            lastLine = line

    return lastLine


def getSanitizedAssertionPattern(msgs):
    '''
    This method provides a way to strip out unwanted dynamic information
    from assertions and replace it with pattern matching elements, e.g.
    for use in signature matching.

    @type msgs: string or list
    @param msgs: Assertion message(s) to be sanitized

    @rtype: string
    @return: Sanitized assertion message (regular expression)
    '''
    assert msgs != None


    returnList = True
    if not isinstance(msgs, list):
        msgs = [ msgs ]
        returnList = False

    sanitizedMsgs = []

    for msg in msgs:
        sanitizedMsg = escapePattern(msg)

        replacementPatterns = []

        # Replace everything that looks like a memory address
        replacementPatterns.append("0x[0-9a-fA-F]+")

        # Strip line numbers as they can easily change across versions
        replacementPatterns.append(":[0-9]+")
        replacementPatterns.append(", line [0-9]+")

        # Strip full path
        replacementPatterns.append(" /.+/")

        # Replace larger numbers, assuming that 1-digit numbers are likely
        # some constant that doesn't need sanitizing.
        replacementPatterns.append("[0-9]{2,}")

        for replacementPattern in replacementPatterns:
            sanitizedMsg = re.sub(replacementPattern, replacementPattern, sanitizedMsg)

        sanitizedMsgs.append(sanitizedMsg)

    if not returnList:
        return sanitizedMsgs[0]

    return sanitizedMsgs


def escapePattern(msg):
    '''
    This method escapes regular expression characters in the string.
    And no, this is not re.escape, which would escape many more characters.

    @type msg: string
    @param msg: String that needs to be quoted

    @rtype: string
    @return: Escaped string for use in regular expressions
    '''

    escapedStr = msg

    activeChars = [ "\\", "[", "]", "{", "}", "(", ")", "*", "+", "-", "?", "^", "$", ".", "|" ]

    for activeChar in activeChars:
        escapedStr = escapedStr.replace(activeChar, "\\" + activeChar)

    return escapedStr
