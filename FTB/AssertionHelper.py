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


RE_ASSERTION = re.compile(r"^ASSERTION \d+: \(.+\)")
RE_MOZ_CRASH = re.compile(r"Hit MOZ_CRASH\([^\)]")
RE_MOZ_CRASH_END = re.compile(r".*\) at .+?:\d+$")
RE_PID = re.compile(r"^\[\d+\]\s+")
RE_RUST_ASSERT = re.compile(r"^thread .*? panicked at '.+$")
RE_RUST_END = re.compile(r".+?\.rs(:\d+)+$")
RE_V8_END = re.compile(r"^")


def getAssertion(output):
    '''
    This helper method provides a way to extract and process the
    different types of assertions from a given buffer.
    The problem here is that pretty much every software has its
    own type of assertions with different output formats.

    @type output: list
    @param output: List of strings to be searched
    '''
    lastLine = None
    endRegex = None

    # Use this to ignore the ASan head line in case of an assertion
    haveFatalAssertion = False

    # Used to only accept the initial MOZ_CRASH() line
    haveMozCrashLine = False

    # The self-hosted JS asserts are followed by an additional regular
    # JS assertion which we need to ignore in that case
    haveSelfHostedJSAssert = False

    for line in output:
        # Remove any PID output at the beginning of the line
        line = re.sub(RE_PID, "", line, count=1)

        if endRegex is not None:
            lastLine.append(line)
            if endRegex.search(line) is not None:
                endRegex = None
        elif line.startswith("Assertion failure"):
            # Firefox fatal assertion (MOZ_ASSERT, JS_ASSERT)

            # If we've seen a self-hosted JS assertion, then we ignore
            # the regular assertion that follows it which will always
            # be "Assertion failure: false" to abort the program.
            if haveSelfHostedJSAssert and "false" in line:
                continue

            lastLine = line
            haveFatalAssertion = True
        elif "panicked at" in line and RE_RUST_ASSERT.match(line) is not None:
            # Is this a single line assert?
            if RE_RUST_END.search(line) is None:
                endRegex = RE_RUST_END
                lastLine = [line]
            else:
                lastLine = line
            haveFatalAssertion = True
        elif line.startswith("# Fatal error in"):
            # Support v8 non-standard multi-line assertion output
            # We need to return this as array so we can create two
            # symptoms for it as the matchers work by line.
            endRegex = RE_V8_END
            lastLine = [line]
            haveFatalAssertion = True
        elif "Assertion" in line and "failed" in line:
            # Firefox ANGLE assertion
            lastLine = line
        elif ": failed assertion" in line:
            # Firefox Skia assertion (SkASSERT)
            lastLine = line
            haveFatalAssertion = True
        elif ": fatal error: \"assert" in line:
            # Skia assertion
            lastLine = line
            haveFatalAssertion = True
        elif line.startswith("ASSERTION") and RE_ASSERTION.search(line):
            lastLine = line
            haveFatalAssertion = True
        elif (not haveFatalAssertion and not haveMozCrashLine and
                "MOZ_CRASH" in line and RE_MOZ_CRASH.search(line)):
            # MOZ_CRASH line, but with a message (we should only look at these)
            if RE_MOZ_CRASH_END.search(line) is None:
                endRegex = RE_MOZ_CRASH_END
                lastLine = [line]
            else:
                lastLine = line
            haveMozCrashLine = True
        elif "Self-hosted JavaScript assertion info" in line:
            lastLine = line
            haveSelfHostedJSAssert = True
            haveFatalAssertion = True
        elif "terminate called after throwing an instance of" in line:
            # C++ unhandled exception
            lastLine = line
            haveFatalAssertion = True
        elif line.startswith("[Non-crash bug] "):
            # Magic string "added" to stderr by some fuzzers.
            lastLine = line

    return lastLine


def getAuxiliaryAbortMessage(output):
    '''
    This helper method provides a way to extract and process additional
    abort messages or other useful messages produced by helper tools like
    sanitizers. These messages can be helpful in signatures if there is no
    abort message from the program itself.

    @type output: list
    @param output: List of strings to be searched
    '''
    lastLine = None
    needASanRW = False
    needTSanRW = False

    for line in output:
        # Remove any PID output at the beginning of the line
        line = re.sub("^\\[\\d+\\]\\s+", "", line, count=1)

        if "ERROR: AddressSanitizer" in line:
            if "failed to allocate" in line:
                lastLine = line.split(": ", 1)[-1].strip()
            elif "SEGV on unknown address" not in line:
                # Strip address, registers and PID prefix
                line = re.sub(r"on address 0x[0-9a-f]+", "", line)
                line = re.sub(r"(at |\()pc 0x[0-9a-f]+", "", line)
                line = re.sub(r"bp 0x[0-9a-f]+", "", line)
                line = re.sub(r"sp 0x[0-9a-f]+", "", line)
                line = re.sub(r"(\(thread\s)?T[0-9]+\)", "", line)
                line = re.sub(r"^[0-9=]+", "", line)
                lastLine = line.strip()
                needASanRW = True
        elif needASanRW and "READ of size" in line or "WRITE of size" in line:
            lastLine = [lastLine]
            lastLine.append(line)
            needASanRW = False
        elif "WARNING: ThreadSanitizer:" in line:
            line = re.sub(r"\s*\(pid=\d+\)", "", line)
            lastLine = line.strip()

            # If we have a data race, then we would like the read/write lines mentioning the threads involved
            needTSanRW = "data race" in line

            if needTSanRW:
                lastLine = [lastLine]
        elif needTSanRW and re.match(r"\s*(?:Previous )?(?:[Aa]tomic )?(?:[Rr]ead|[Ww]rite) of size", line):
            lastLine.append(line.strip())
        elif "glibc detected" in line:
            # Aborts caused by glibc runtime error detection
            lastLine = line
        elif "runtime error" in line and re.search(":\\d+:\\d+: runtime error: ", line):
            # UBSan error
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
    assert msgs is not None

    returnList = True
    if not isinstance(msgs, list):
        msgs = [msgs]
        returnList = False

    sanitizedMsgs = []

    for msg in msgs:
        # remember the position of all backslashes in the input
        bsPositions = []
        for chunk in msg.split("\\"):
            if not bsPositions:
                bsPositions.append(len(chunk))
            else:
                bsPositions.append(len(chunk) + bsPositions[-1] + 1)
        bsPositions.pop()  # msg.split(x) will return `# of matches(x) + 1` values: the last one is invalid

        # replace backslashes with forward slashes for now so we can process paths consistently
        # any backslashes not matched in a path pattern will be restored later
        sanitizedMsg = escapePattern(msg.replace("\\", "/"))

        # correct bsPositions for escaped characters
        idx = 0
        for chunk in sanitizedMsg.split("\\"):
            idx += len(chunk) + 1
            bsPositions = [bs + 1 if bs > idx else bs for bs in bsPositions]

        replacementPatterns = []

        # Specific TSan patterns
        replacementPatterns.append("(Previous )?[Aa]tomic [Rr]ead of size")
        replacementPatterns.append("(Previous )?[Aa]tomic [Ww]rite of size")
        replacementPatterns.append("(Previous )?[Rr]ead of size")
        replacementPatterns.append("(Previous )?[Ww]rite of size")
        # We avoid the use of parentheses here because they would be double-escaped
        replacementPatterns.append("thread T[0-9]+( .+mutexes: .+)?:")
        replacementPatterns.append("by main thread( .+mutexes: .+)?:")

        # Replace everything that looks like a memory address
        replacementPatterns.append("0x[0-9a-fA-F]+")

        # Strip line numbers as they can easily change across versions
        replacementPatterns.append("(:[0-9]+)+")
        replacementPatterns.append(", line [0-9]+")

        # Replace rust thread #s
        replacementPatterns.append("Thread#[0-9]+' panicked")

        # Strip full paths
        pathPattern = "([a-zA-Z]:)?/.+/"

        # In order to reliably identify paths, we require them to be prefixed
        # by some character that doesn't belong to the path. It turns out that
        # spaces, quotes and comma are the only things used in the assertions
        # we support so far. However, we don't want to group these characters
        # into a regex so avoid cluttering the signature too much.
        replacementPatterns.append(" " + pathPattern)
        replacementPatterns.append("'" + pathPattern)
        replacementPatterns.append('"' + pathPattern)
        replacementPatterns.append(',' + pathPattern)

        # Replace larger numbers, assuming that 1-digit numbers are likely
        # some constant that doesn't need sanitizing.
        replacementPatterns.append("[0-9]{2,}")

        for replacementPattern in replacementPatterns:
            def _handleMatch(match):
                start = match.start(0)
                end = match.end(0)
                lengthDiff = len(replacementPattern) - len(match.group(0))

                # we can't replace bsPositions with list comprehensions because we're in a nested scope
                # iterate by index and modify it instead
                idx = 0
                while idx < len(bsPositions):
                    if bsPositions[idx] < start:
                        # no change for backslashes before the start of this match
                        idx += 1
                    elif bsPositions[idx] < end:
                        # the backslash is covered by this match, remove it
                        bsPositions.pop(idx)
                    else:
                        # the backslash is after the match, shift it by the length difference
                        bsPositions[idx] += lengthDiff
                        idx += 1

                return replacementPattern

            sanitizedMsg = re.sub(replacementPattern, _handleMatch, sanitizedMsg)

        # backslashes were replaced with / for unified path handling
        # (and because backslash is the escape character, which makes pattern matching otherwise impossible)
        # if they were not used in a path pattern, restore them now
        # in other words, add back the windows bs
        while bsPositions:
            bsPos = bsPositions.pop()
            # escape it now too, since it would have gone through escapePattern above
            sanitizedMsg = sanitizedMsg[:bsPos] + "\\\\" + sanitizedMsg[bsPos + 1:]

        # Some implementations wrap the path into parentheses. We cannot add this to
        # replacementPatterns because it would double-escape the leading parenthesis.
        sanitizedMsg = re.sub('\\(' + pathPattern, '(' + pathPattern, sanitizedMsg)

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

    activeChars = ("\\", "[", "]", "{", "}", "(", ")", "*", "+", "?", "^", "$", ".", "|")

    for activeChar in activeChars:
        if activeChar in escapedStr:
            escapedStr = escapedStr.replace(activeChar, "\\" + activeChar)

    return escapedStr
