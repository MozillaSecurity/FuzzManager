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
import json

import six

from FTB.Signatures import JSONHelper
from FTB.Signatures.Matchers import StringMatch, NumberMatch


@six.add_metaclass(ABCMeta)
class Symptom(object):
    '''
    Abstract base class that provides a method to instantiate the right sub class.
    It also supports generating a CrashSignature based on the stored information.
    '''
    def __init__(self, jsonObj):
        # Store the original source so we can return it if someone wants to stringify us
        self.jsonsrc = json.dumps(jsonObj, indent=2)
        self.jsonobj = jsonObj

    def __str__(self):
        return self.jsonsrc

    @staticmethod
    def fromJSONObject(obj):
        '''
        Create the appropriate Symptom based on the given object (decoded from JSON)

        @type obj: map
        @param obj: Object as decoded from JSON

        @rtype: Symptom
        @return: Symptom subclass instance matching the given object
        '''
        if "type" not in obj:
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
        elif (stype == "testcase"):
            return TestcaseSymptom(obj)
        elif (stype == "stackFrames"):
            return StackFramesSymptom(obj)
        else:
            raise RuntimeError("Unknown symptom type: %s" % stype)

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
        Symptom.__init__(self, obj)
        self.output = StringMatch(JSONHelper.getObjectOrStringChecked(obj, "value", True))
        self.src = JSONHelper.getStringChecked(obj, "src")

        if self.src is not None:
            self.src = self.src.lower()
            if self.src != "stderr" and self.src != "stdout" and self.src != "crashdata":
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

        if self.src is None:
            checkedOutput.extend(crashInfo.rawStdout)
            checkedOutput.extend(crashInfo.rawStderr)
            checkedOutput.extend(crashInfo.rawCrashData)
        elif (self.src == "stdout"):
            checkedOutput = crashInfo.rawStdout
        elif (self.src == "stderr"):
            checkedOutput = crashInfo.rawStderr
        else:
            checkedOutput = crashInfo.rawCrashData

        windowsSlashWorkaround = crashInfo.configuration.os == "windows"
        for line in reversed(checkedOutput):
            if self.output.matches(line, windowsSlashWorkaround=windowsSlashWorkaround):
                return True

        return False


class StackFrameSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        Symptom.__init__(self, obj)
        self.functionName = StringMatch(JSONHelper.getNumberOrStringChecked(obj, "functionName", True))
        self.frameNumber = JSONHelper.getNumberOrStringChecked(obj, "frameNumber")

        if self.frameNumber is not None:
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
        Symptom.__init__(self, obj)
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
        Symptom.__init__(self, obj)
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
        Symptom.__init__(self, obj)
        self.registerNames = JSONHelper.getArrayChecked(obj, "registerNames")
        self.instructionName = JSONHelper.getObjectOrStringChecked(obj, "instructionName")

        if self.instructionName is not None:
            self.instructionName = StringMatch(self.instructionName)
        elif self.registerNames is None or len(self.registerNames) == 0:
            raise RuntimeError("Must provide at least instruction name or register names")

    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information

        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against

        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''
        if crashInfo.crashInstruction is None:
            # No crash instruction available, do not match
            return False

        if self.registerNames is not None:
            for register in self.registerNames:
                if register not in crashInfo.crashInstruction:
                    return False

        if self.instructionName is not None:
            if not self.instructionName.matches(crashInfo.crashInstruction):
                return False

        return True


class TestcaseSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        Symptom.__init__(self, obj)
        self.output = StringMatch(JSONHelper.getObjectOrStringChecked(obj, "value", True))

    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information

        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against

        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''

        # No testcase means to fail matching
        if crashInfo.testcase is None:
            return False

        testLines = crashInfo.testcase.splitlines()

        for line in testLines:
            if self.output.matches(line):
                return True

        return False


class StackFramesSymptom(Symptom):
    def __init__(self, obj):
        '''
        Private constructor, called by L{Symptom.fromJSONObject}. Do not use directly.
        '''
        Symptom.__init__(self, obj)
        self.functionNames = []

        rawFunctionNames = JSONHelper.getArrayChecked(obj, "functionNames", True)

        for fn in rawFunctionNames:
            self.functionNames.append(StringMatch(fn))

    def matches(self, crashInfo):
        '''
        Check if the symptom matches the given crash information

        @type crashInfo: CrashInfo
        @param crashInfo: The crash information to check against

        @rtype: bool
        @return: True if the symptom matches, False otherwise
        '''

        return StackFramesSymptom._match(crashInfo.backtrace, self.functionNames)

    def diff(self, crashInfo):
        if self.matches(crashInfo):
            return (0, None)

        for depth in range(1, 4):
            (bestDepth, bestGuess) = StackFramesSymptom._diff(crashInfo.backtrace, self.functionNames, 0, 1, depth)
            if bestDepth is not None:
                guessedFunctionNames = [repr(x) for x in bestGuess]

                # Remove trailing wildcards as they are of no use
                while guessedFunctionNames and (guessedFunctionNames[-1] == '?' or guessedFunctionNames[-1] == '???'):
                    guessedFunctionNames.pop()

                if not guessedFunctionNames:
                    # Do not return empty matches. This happens if there's nothing left except wildcards.
                    return (None, None)

                return (bestDepth, StackFramesSymptom({"type": "stackFrames", 'functionNames': guessedFunctionNames}))

        return (None, None)

    @staticmethod
    def _diff(stack, signatureGuess, startIdx, depth, maxDepth):
        singleWildcardMatch = StringMatch("?")

        newSignatureGuess = []
        newSignatureGuess.extend(signatureGuess)

        bestDepth = None
        bestGuess = None

        hasVariableStackLengthQuantifier = '???' in [str(x) for x in newSignatureGuess]

        for idx in range(startIdx, len(newSignatureGuess)):
            if idx == startIdx or (str(newSignatureGuess[idx - 1]) != '?' and str(newSignatureGuess[idx - 1]) != '???'):
                # Inserting '?' after another '?' or '???' does not make a difference
                # because it is equivalent to inserting it before that last wildcard itself.

                newSignatureGuess.insert(idx, singleWildcardMatch)

                # Check if we have a match with our modification
                if StackFramesSymptom._match(stack, newSignatureGuess):
                    return (depth, newSignatureGuess)

                # If we don't have a match but we're not at our current depth limit,
                # add one more level of depth for our search.
                if depth < maxDepth:
                    (newBestDepth, newBestGuess) = StackFramesSymptom._diff(stack, newSignatureGuess, idx,
                                                                            depth + 1, maxDepth)

                    if newBestDepth is not None and (bestDepth is None or newBestDepth < bestDepth):
                        bestDepth = newBestDepth
                        bestGuess = newBestGuess

                newSignatureGuess.pop(idx)

            # Now repeat the same with replacing instead of adding
            # unless the match at idx is a wildcard itself

            if str(newSignatureGuess[idx]) == '?' or str(newSignatureGuess[idx]) == '???':
                continue

            newMatch = singleWildcardMatch
            if not hasVariableStackLengthQuantifier and len(stack) > idx:
                # We can perform some optimizations here if we have a signature that does
                # not contain any quantifiers that can match multiple stack frames.

                if newSignatureGuess[idx].matches(stack[idx]):
                    # Our frame matches, so it doesn't make sense to try and mess with it
                    continue

                if not newSignatureGuess[idx].isPCRE:
                    # If our match is not PCRE, try some heuristics to generalize the match

                    if stack[idx] in str(newSignatureGuess[idx]):
                        # The stack frame is a substring of the what we try to match,
                        # use the stack frame as new matcher to ensure a match without
                        # using a wildcard.
                        newMatch = StringMatch(stack[idx])

            origMatch = newSignatureGuess[idx]
            newSignatureGuess[idx] = newMatch

            # Check if we have a match with our modification
            if StackFramesSymptom._match(stack, newSignatureGuess):
                return (depth, newSignatureGuess)

            # If we don't have a match but we're not at our current depth limit,
            # add one more level of depth for our search.
            if depth < maxDepth:
                (newBestDepth, newBestGuess) = StackFramesSymptom._diff(stack, newSignatureGuess, idx,
                                                                        depth + 1, maxDepth)

                if newBestDepth is not None and (bestDepth is None or newBestDepth < bestDepth):
                    bestDepth = newBestDepth
                    bestGuess = newBestGuess

            newSignatureGuess[idx] = origMatch

        return (bestDepth, bestGuess)

    @staticmethod
    def _match(partialStack, partialFunctionNames):

        while True:

            # Process as many non-wildcard chars as we can find iteratively for performance reasons
            while partialFunctionNames and partialStack and str(partialFunctionNames[0]) not in {'?', '???'}:
                if not partialFunctionNames[0].matches(partialStack[0]):
                    return False

                # Change the view on partialStack and partialFunctionNames without actually
                # modifying the underlying arrays. They have to be preserved for the caller.
                partialStack = partialStack[1:]
                partialFunctionNames = partialFunctionNames[1:]

            if not partialFunctionNames:
                # End of function names to match, accept
                return True

            if str(partialFunctionNames[0]) in {'?', '???'}:
                if StackFramesSymptom._match(partialStack, partialFunctionNames[1:]):
                    # We recursively consumed 0 to N stack frames and can now
                    # get a match for the remaining stack without the current
                    # wildcard element, so we're done and accept the stack.
                    return True
                else:
                    if not partialStack:
                        # Out of stack to match, reject
                        return False

                    # Consume one stack frame and continue
                    partialStack = partialStack[1:]

                    if str(partialFunctionNames[0]) == '?':
                        # Consume the question mark too
                        partialFunctionNames = partialFunctionNames[1:]

            elif not partialStack:
                # Out of stack to match, reject
                return False
