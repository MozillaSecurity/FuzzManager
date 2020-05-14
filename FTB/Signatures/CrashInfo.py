'''
Crash Information

Represents information about a crash. Specific subclasses implement
different crash data supported by the implementation.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

from abc import ABCMeta
import json
import os
import re
import sys

import six

from FTB import AssertionHelper
from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures import RegisterHelper
from FTB.Signatures.CrashSignature import CrashSignature


def uint32(val):
    '''Force `val` into unsigned 32-bit range.

    Note that the input is returned as an int, therefore
    any math on the result may no longer be in uint32 range.

    >>> uint32(0x100000000)
    0
    >>> uint32(-1)
    4294967295
    >>> uint32(0xFFFFFFF0)
    4294967280
    >>> uint32(0x7FFFFFFF)
    2147483647
    >>> uint32(0x80000000)
    2147483648
    '''
    return val & 0xFFFFFFFF


def int32(val):
    '''Force `val` into signed 32-bit range.

    Note that the input is returned as an int, therefore
    any math on the result may no longer be in int32 range.

    >>> int32(0x100000000)
    0
    >>> int32(-1)
    -1
    >>> int32(0xFFFFFFF0)
    -16
    >>> int32(0x7FFFFFFF)
    2147483647
    >>> int32(0x80000000)
    -2147483648
    '''
    val = uint32(val)
    if val.bit_length() == 32:
        val = val - 0x100000000
    return val


def uint64(val):
    '''Force `val` into unsigned 64-bit range.

    Note that the input is returned as an int, therefore
    any math on the result may no longer be in uint64 range.

    >>> uint64(0x10000000000000000)
    0
    >>> uint64(-1)
    18446744073709551615
    >>> uint64(0xFFFFFFFFFFFFFFF0)
    18446744073709551600
    >>> uint64(0x7FFFFFFFFFFFFFFF)
    9223372036854775807
    >>> uint64(0x8000000000000000)
    9223372036854775808
    '''
    return val & 0xFFFFFFFFFFFFFFFF


def int64(val):
    '''Force `val` into signed 64-bit range.

    Note that the input is returned as an int, therefore
    any math on the result may no longer be in int64 range.

    >>> int64(0x10000000000000000)
    0
    >>> int64(-1)
    -1
    >>> int64(0xFFFFFFFFFFFFFFF0)
    -16
    >>> int64(0x7FFFFFFFFFFFFFFF)
    9223372036854775807
    >>> int64(0x8000000000000000)
    -9223372036854775808
    '''
    val = uint64(val)
    if val.bit_length() == 64:
        val = val - 0x10000000000000000
    return val


@six.add_metaclass(ABCMeta)
class CrashInfo(object):
    '''
    Abstract base class that provides a method to instantiate the right sub class.
    It also supports generating a CrashSignature based on the stored information.
    '''
    def __init__(self):
        # Store the raw data
        self.rawStdout = []
        self.rawStderr = []
        self.rawCrashData = []

        # Store processed data
        self.backtrace = []
        self.registers = {}
        self.crashAddress = None
        self.crashInstruction = None

        # Store configuration data (platform, product, os, etc.)
        self.configuration = None

        # This is an optional testcase that is not stored with the crashInfo but
        # can be "attached" before matching signatures that might require the
        # testcase.
        self.testcase = None

        # This can be used to record failures during signature creation
        self.failureReason = None

    def __str__(self):
        buf = []
        buf.append("Crash trace:")
        buf.append("")
        for idx, frame in enumerate(self.backtrace):
            buf.append("# %02d    %s" % (idx, frame))
        buf.append("")

        if self.crashAddress:
            buf.append("Crash address: 0x%x" % self.crashAddress)

        if self.crashInstruction:
            buf.append("Crash instruction: %s" % self.crashInstruction)

        if self.crashAddress or self.crashInstruction:
            buf.append("")

        buf.append("Last 5 lines on stderr:")
        buf.extend(self.rawStderr[-5:])

        return "\n".join(buf)

    def toCacheObject(self):
        '''
        Create a cache object for restoring the class instance later on without parsing
        the crash data again. This object includes all class fields except for the
        storage heavy raw objects like stdout, stderr and raw crashdata.

        @rtype: dict
        @return: Dictionary containing expensive class fields
        '''
        cacheObject = {}
        cacheObject['backtrace'] = self.backtrace
        cacheObject['registers'] = self.registers

        if self.crashAddress is not None:
            cacheObject['crashAddress'] = int(self.crashAddress)
        else:
            cacheObject['crashAddress'] = None

        cacheObject['crashInstruction'] = self.crashInstruction
        cacheObject['failureReason'] = self.failureReason

        return cacheObject

    @staticmethod
    def fromRawCrashData(stdout, stderr, configuration, auxCrashData=None, cacheObject=None):
        '''
        Create appropriate CrashInfo instance from raw crash data

        @type stdout: List of strings
        @param stdout: List of lines as they appeared on stdout
        @type stderr: List of strings
        @param stderr: List of lines as they appeared on stderr
        @type configuration: ProgramConfiguration
        @param configuration: Exact program configuration that is associated with the crash
        @type auxCrashData: List of strings
        @param auxCrashData: Optional additional crash output (e.g. GDB). If not specified, stderr is used.
        @type cacheObject: Dictionary
        @param cacheObject: The cache object that should be used to restore the class fields
                            instead of parsing the crash data. The appropriate object can be
                            created by calling the toCacheObject method.

        @rtype: CrashInfo
        @return: Crash information object
        '''

        assert stdout is None or isinstance(stdout, (list, six.text_type, bytes))
        assert stderr is None or isinstance(stderr, (list, six.text_type, bytes))
        assert auxCrashData is None or isinstance(auxCrashData, (list, six.text_type, bytes))

        assert isinstance(configuration, ProgramConfiguration)

        if isinstance(stdout, (six.text_type, bytes)):
            stdout = stdout.splitlines()

        if isinstance(stderr, (six.text_type, bytes)):
            stderr = stderr.splitlines()

        if isinstance(auxCrashData, (six.text_type, bytes)):
            auxCrashData = auxCrashData.splitlines()

        if cacheObject is not None:
            c = CrashInfo()

            if stdout is not None:
                c.rawStdout.extend(stdout)

            if stderr is not None:
                c.rawStderr.extend(stderr)

            if auxCrashData is not None:
                c.rawCrashData.extend(auxCrashData)

            c.configuration = configuration
            c.backtrace = cacheObject['backtrace']
            c.registers = cacheObject['registers']
            c.crashAddress = cacheObject['crashAddress']
            c.crashInstruction = cacheObject['crashInstruction']
            c.failureReason = cacheObject['failureReason']

            return c

        # some results are weak, meaning any other CrashInfo detected after it will take precedence
        weakResult = None

        asanString = "ERROR: AddressSanitizer"
        gdbString = "received signal SIG"
        gdbCoreString = "Program terminated with signal "
        lsanString = "ERROR: LeakSanitizer:"
        tsanString = "WARNING: ThreadSanitizer:"
        ubsanString = ": runtime error: "
        ubsanString2 = "ERROR: UndefinedBehaviorSanitizer"
        ubsanRegex = r".+?:\d+:\d+: runtime error:\s+.+"
        appleString = "Mac OS X"
        cdbString = "Microsoft (R) Windows Debugger"

        # Use two strings for detecting rust backtraces to avoid false positives
        rustFirstString = "panicked at"
        rustSecondString = "stack backtrace:"
        rustFirstDetected = False

        # Use two strings for detecting Minidumps to avoid false positives
        minidumpFirstString = "OS|"
        minidumpSecondString = "CPU|"
        minidumpFirstDetected = False

        # Search both crashData and stderr, but prefer crashData
        lines = []
        if auxCrashData is not None:
            lines.extend(auxCrashData)
        if stderr is not None:
            lines.extend(stderr)

        result = None
        for line in lines:
            if ubsanString in line and re.match(ubsanRegex, line) is not None:
                result = UBSanCrashInfo(stdout, stderr, configuration, auxCrashData)
                break
            elif asanString in line or ubsanString2 in line:
                result = ASanCrashInfo(stdout, stderr, configuration, auxCrashData)
                break
            elif lsanString in line:
                result = LSanCrashInfo(stdout, stderr, configuration, auxCrashData)
                break
            elif tsanString in line:
                result = TSanCrashInfo(stdout, stderr, configuration, auxCrashData)
                break
            elif appleString in line and not line.startswith(minidumpFirstString):
                result = AppleCrashInfo(stdout, stderr, configuration, auxCrashData)
                break
            elif cdbString in line:
                result = CDBCrashInfo(stdout, stderr, configuration, auxCrashData)
                break
            elif gdbString in line or gdbCoreString in line:
                result = GDBCrashInfo(stdout, stderr, configuration, auxCrashData)
                break
            elif not rustFirstDetected and rustFirstString in line:
                rustFirstDetected = True
                minidumpFirstDetected = False
            elif rustFirstDetected and rustSecondString in line:
                weakResult = RustCrashInfo(stdout, stderr, configuration, auxCrashData)
                rustFirstDetected = False
            elif not minidumpFirstDetected and minidumpFirstString in line:
                # Only match Minidump output if the *next* line also contains
                # the second search string defined above.
                rustFirstDetected = False
                minidumpFirstDetected = True
            elif minidumpFirstDetected and minidumpSecondString in line:
                result = MinidumpCrashInfo(stdout, stderr, configuration, auxCrashData)
                break
            elif line.startswith("==") and re.match(ValgrindCrashInfo.MSG_REGEX, line):
                result = ValgrindCrashInfo(stdout, stderr, configuration, auxCrashData)
                break
            else:
                minidumpFirstDetected = False

        # Default fallback to be used if there is neither ASan nor GDB output.
        # This is still useful in case there is no crash but we want to match
        # e.g. stdout/stderr output with signatures.
        if result is None:
            result = weakResult or NoCrashInfo(stdout, stderr, configuration, auxCrashData)

        # Rust symbols have a source hash appended to them. Strip this off regardless of the
        # CrashInfo type
        result.backtrace = [re.sub(r"::h[0-9a-f]{16}$", "", frame) for frame in result.backtrace]

        return result

    def createShortSignature(self):
        '''
        @rtype: String
        @return: A string representing this crash (short signature)
        '''
        # See if we have an abort message and if so, use that as short signature
        abortMsg = AssertionHelper.getAssertion(self.rawStderr)

        # See if we have an abort message in our crash data maybe
        if not abortMsg and self.rawCrashData:
            abortMsg = AssertionHelper.getAssertion(self.rawCrashData)

        if abortMsg is not None:
            if isinstance(abortMsg, list):
                return " ".join(abortMsg)
            else:
                return abortMsg

        if not self.backtrace:
            return "No crash detected"

        return "[@ %s]" % self.backtrace[0]

    def createCrashSignature(self, forceCrashAddress=False, forceCrashInstruction=False, maxFrames=8,
                             minimumSupportedVersion=13):
        '''
        @param forceCrashAddress: If True, the crash address will be included in any case
        @type forceCrashAddress: bool
        @param forceCrashInstruction: If True, the crash instruction will be included in any case
        @type forceCrashInstruction: bool
        @param maxFrames: How many frames (at most) should be included in the signature
        @type maxFrames: int

        @param minimumSupportedVersion: The minimum crash signature standard version that the
                                        generated signature should be valid for (10 => 1.0, 13 => 1.3)
        @type minimumSupportedVersion: int

        @rtype: CrashSignature
        @return: A crash signature object
        '''
        # Determine the actual number of frames based on how many we got
        if len(self.backtrace) > maxFrames:
            numFrames = maxFrames
        else:
            numFrames = len(self.backtrace)

        symptomArr = []

        # Memorize where we find our abort messages
        abortMsgInCrashdata = False

        # See if we have an abort message and if so, get a sanitized version of it
        abortMsgs = AssertionHelper.getAssertion(self.rawStderr)

        if abortMsgs is None and minimumSupportedVersion >= 13:
            # Look for abort messages also inside crashdata
            # only on version 1.3 or higher, because the "crashdata" source
            # type for output matching was added in that version.
            abortMsgs = AssertionHelper.getAssertion(self.rawCrashData)
            if abortMsgs is not None:
                abortMsgInCrashdata = True

        # Still no abort message, fall back to auxiliary abort messages (ASan/UBSan)
        if abortMsgs is None:
            abortMsgs = AssertionHelper.getAuxiliaryAbortMessage(self.rawStderr)

        if abortMsgs is None and minimumSupportedVersion >= 13:
            # Look for auxiliary abort messages also inside crashdata
            # only on version 1.3 or higher, because the "crashdata" source
            # type for output matching was added in that version.
            abortMsgs = AssertionHelper.getAuxiliaryAbortMessage(self.rawCrashData)
            if abortMsgs is not None:
                abortMsgInCrashdata = True

        if abortMsgs is not None:
            if not isinstance(abortMsgs, list):
                abortMsgs = [abortMsgs]

            for abortMsg in abortMsgs:
                abortMsg = AssertionHelper.getSanitizedAssertionPattern(abortMsg)
                abortMsgSrc = "stderr"
                if abortMsgInCrashdata:
                    abortMsgSrc = "crashdata"

                # Compose StringMatch object with PCRE pattern.
                # Versions below 1.2 only support the full object PCRE style,
                # for anything newer, use the short form with forward slashes
                # to increase the readability of the signatures.
                if minimumSupportedVersion < 12:
                    stringObj = {"value": abortMsg, "matchType": "pcre"}
                    symptomObj = {"type": "output", "src": abortMsgSrc, "value": stringObj}
                else:
                    symptomObj = {"type": "output", "src": abortMsgSrc, "value": "/%s/" % abortMsg}
                symptomArr.append(symptomObj)

        # Consider the first four frames as top stack
        topStackLimit = 4

        # If we have less than topStackLimit frames available anyway, count the difference
        # between topStackLimit and the available frames already as missing.
        # E.g. if the trace has only three entries anyway, one will be considered missing
        # right from the start. This should prevent that very short stack frames are used
        # for signatures without additional crash information that narrows the signature.

        if numFrames >= topStackLimit:
            topStackMissCount = 0
        else:
            topStackMissCount = topStackLimit - numFrames

        # StackFramesSymptom is only supported in 1.2 and higher,
        # for everything else, use multiple stackFrame symptoms
        if minimumSupportedVersion < 12:
            for idx in range(0, numFrames):
                functionName = self.backtrace[idx]
                if not functionName == "??":
                    symptomObj = {"type": "stackFrame", "frameNumber": idx, "functionName": functionName}
                    symptomArr.append(symptomObj)
                elif idx < 4:
                    # If we're in the top 4, we count this as a miss
                    topStackMissCount += 1
        else:
            framesArray = []

            for idx in range(0, numFrames):
                functionName = self.backtrace[idx]
                if not functionName == "??":
                    framesArray.append(functionName)
                else:
                    framesArray.append("?")
                    if idx < 4:
                        # If we're in the top 4, we count this as a miss
                        topStackMissCount += 1

            lastSymbolizedFrame = None
            for frameIdx in range(0, len(framesArray)):
                if str(framesArray[frameIdx]) != '?':
                    lastSymbolizedFrame = frameIdx

            if lastSymbolizedFrame is not None:
                # Remove all elements behind the last symbolized frame
                framesArray = framesArray[:lastSymbolizedFrame + 1]
            else:
                # We don't have a single symbolized frame, so it doesn't make sense
                # to keep any wildcards in case we added some for unsymbolized frames.
                framesArray = []

            if framesArray:
                symptomArr.append({"type": "stackFrames", "functionNames": framesArray})

        # Missing too much of the top stack frames, add additional crash information
        stackIsInsufficient = topStackMissCount >= 2 and abortMsgs is None

        includeCrashAddress = stackIsInsufficient or forceCrashAddress
        includeCrashInstruction = (stackIsInsufficient and self.crashInstruction is not None) or forceCrashInstruction

        if not symptomArr and not includeCrashInstruction:
            # If at this point, we don't have any symptoms from either backtrace
            # or abort messages and we also lack a crash instruction, then the
            # the only potential symptom that remains is the crash address.
            # That symptom alone would in most cases be too broad for an automatically
            # generated signature, so we stop at this point.
            self.failureReason = "Insufficient data to generate crash signature."
            return None

        if includeCrashAddress:
            if self.crashAddress is None:
                crashAddress = ""
            elif self.crashAddress < 0x100:
                # Try to match crash addresses that are small but non-zero
                # with a generic range that is likely associated with null-deref.
                crashAddress = "< 0x100"
            else:
                crashAddress = "> 0xFF"

            crashAddressSymptomObj = {"type": "crashAddress", "address": crashAddress}
            symptomArr.append(crashAddressSymptomObj)

        if includeCrashInstruction:
            if self.crashInstruction is None:
                failureReason = self.failureReason
                self.failureReason = "No crash instruction available from crash data. Reason: %s" % failureReason
                return None

            crashInstructionSymptomObj = {"type": "instruction", "instructionName": self.crashInstruction}
            symptomArr.append(crashInstructionSymptomObj)

        sigObj = {"symptoms": symptomArr}

        return CrashSignature(json.dumps(sigObj, indent=2, sort_keys=True))

    @staticmethod
    def sanitizeStackFrame(frame):
        '''
        This function removes function arguments and other non-generic parts
        of the function frame, returning a (hopefully) generic function name.

        @param frame: The stack frame to sanitize
        @type forceCrashAddress: str

        @rtype: str
        @return: Sanitized stack frame
        '''

        # Remove any trailing const declaration
        if frame.endswith(" const"):
            frame = frame[0:-len(" const")]

        # Strip the last ( ) segment, which might also contain more parentheses
        if frame.endswith(")"):
            idx = len(frame) - 2
            parlevel = 0
            while(idx > 0):
                if frame[idx] == "(":
                    if parlevel > 0:
                        parlevel -= 1
                    else:
                        # Done
                        break
                elif frame[idx] == ")":
                    parlevel += 1

                idx -= 1

            # Only strip if we actually found the ( ) before we reached the
            # beginning of our string.
            if idx:
                frame = frame[:idx]

        if "lambda" in frame:
            frame = re.sub("<lambda at .+?:\\d+:\\d+>", "", frame)

        return frame


class NoCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if crashData is not None:
            self.rawCrashData.extend(crashData)

        self.configuration = configuration


class ASanCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if crashData is not None:
            self.rawCrashData.extend(crashData)

        self.configuration = configuration

        # If crashData is given, use that to find the ASan trace, otherwise use stderr
        asanOutput = crashData if crashData else stderr

        asanCrashAddressPattern = r"""(?x)
                                   \s[A-Za-z]+Sanitizer.*\s
                                     (?:on\saddress             # The most common format, used for all overflows
                                       |on\sunknown\saddress    # Used in case of a SIGSEGV
                                       |double-free\son         # Used in case of a double-free
                                       |failed\sto\sallocate\s0x[0-9a-f]+\s
                                       |negative-size-param:\s*\(size=-\d+\)
                                       |not\smalloc\(\)-ed:     # Used in case of a wild free (on unallocated memory)
                                       |not\sowned:             # Used when calling __asan_get_allocated_size() on a pointer that isn't owned
                                       |\w+-param-overlap:      # Bad memcpy/strcpy/strcat... etc
                                       |requested\sallocation\ssize\s0x[0-9a-f]+\s)
                                   (\s*0x([0-9a-f]+))?"""  # noqa
        asanRegisterPattern = r"(?:\s+|\()pc\s+0x([0-9a-f]+)\s+(sp|bp)\s+0x([0-9a-f]+)\s+(sp|bp)\s+0x([0-9a-f]+)"

        expectedIndex = 0
        reportFound = False
        for traceLine in asanOutput:
            if not reportFound:
                match = re.search(asanCrashAddressPattern, traceLine)
                if match is None:
                    # Not in the ASan output yet.
                    # Some lines in eg. debug+asan builds might error if we continue.
                    continue
                reportFound = True
                try:
                    self.crashAddress = int(match.group(1), 16)
                except TypeError:
                    pass  # No crash address available

                # Crash Address and Registers are in the same line for ASan
                match = re.search(asanRegisterPattern, traceLine)
                # Collect register values if they are available in the ASan trace
                if match is not None:
                    self.registers["pc"] = int(match.group(1), 16)
                    self.registers[match.group(2)] = int(match.group(3), 16)
                    self.registers[match.group(4)] = int(match.group(5), 16)

            parts = traceLine.strip().split()

            # We only want stack frames
            if not parts or not parts[0].startswith("#"):
                continue

            try:
                index = int(parts[0][1:])
            except ValueError:
                continue

            # We may see multiple traces in ASAN
            if index == 0:
                expectedIndex = 0

            if not expectedIndex == index:
                raise RuntimeError("Fatal error parsing ASan trace (Index mismatch, got index %s but expected %s)" %
                                   (index, expectedIndex))

            component = None
            if len(parts) > 2:
                if parts[2] == "in":
                    component = " ".join(parts[3:-1])
                else:
                    # Remove parentheses around component
                    component = parts[2][1:-1]
            else:
                print("Warning: Missing component in this line: %s" % traceLine, file=sys.stderr)
                component = "<missing>"

            self.backtrace.append(CrashInfo.sanitizeStackFrame(component))
            expectedIndex += 1

    def createShortSignature(self):
        '''
        @rtype: String
        @return: A string representing this crash (short signature)
        '''
        # Always prefer using regular program aborts
        abortMsg = AssertionHelper.getAssertion(self.rawStderr)

        # Also check the crash data for program abort data
        # (sometimes happens e.g. with MOZ_CRASH)
        if not abortMsg and self.rawCrashData:
            abortMsg = AssertionHelper.getAssertion(self.rawCrashData)

        if abortMsg is not None:
            if isinstance(abortMsg, list):
                return " ".join(abortMsg)
            else:
                return abortMsg

        # If we don't have a program abort message, see if we have an ASan
        # specific abort message other than a crash message that we can use.
        abortMsg = AssertionHelper.getAuxiliaryAbortMessage(self.rawStderr)

        # Also check the crash data again
        if not abortMsg and self.rawCrashData:
            abortMsg = AssertionHelper.getAuxiliaryAbortMessage(self.rawCrashData)

        if abortMsg is not None:
            rwMsg = None
            if isinstance(abortMsg, list):
                asanMsg = abortMsg[0]
                rwMsg = abortMsg[1]
            else:
                asanMsg = abortMsg

            # Do some additional formatting work for short signature only
            asanMsg = re.sub("^ERROR: ", "", asanMsg)

            # Strip various forms of special thread information and messages
            asanMsg = re.sub(" in thread T.+", "", asanMsg)
            asanMsg = re.sub(r" malloc\(\)\-ed: 0x[0-9a-f]+", r" malloc()-ed", asanMsg)
            asanMsg = re.sub(r"\[0x[0-9a-f]+,0x[0-9a-f]+\) and \[0x[0-9a-f]+, 0x[0-9a-f]+\) overlap$",
                             "overlap", asanMsg)
            asanMsg = re.sub(r"0x[0-9a-f]+\s\(0x[0-9a-f]+\safter\sadjustments.+?\)\s", "", asanMsg)
            asanMsg = re.sub(r"size\sof\s0x[0-9a-f]+$", "size", asanMsg)

            if self.backtrace:
                asanMsg += " [@ %s]" % self.backtrace[0]
            if rwMsg:
                # Strip address and thread
                rwMsg = re.sub(" at 0x[0-9a-f]+ thread .+", "", rwMsg)
                asanMsg += " with %s" % rwMsg

            return asanMsg

        if not self.backtrace:
            if self.crashAddress is not None:
                # We seem to have a crash but no backtrace, so let it show up as a crash with no symbols
                return "[@ ??]"

            return "No crash detected"

        return "[@ %s]" % self.backtrace[0]


class LSanCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if crashData is not None:
            self.rawCrashData.extend(crashData)

        self.configuration = configuration

        # If crashData is given, use that to find the LSan trace, otherwise use stderr
        lsanOutput = crashData if crashData else stderr
        lsanErrorPattern = "ERROR: LeakSanitizer:"
        lsanPatternSeen = False

        expectedIndex = 0
        for traceLine in lsanOutput:
            if not lsanErrorPattern:
                if lsanErrorPattern in traceLine:
                    lsanPatternSeen = True
                continue

            parts = traceLine.strip().split()

            # We only want stack frames
            if not parts or not parts[0].startswith("#"):
                continue

            index = int(parts[0][1:])

            if expectedIndex != index:
                raise RuntimeError("Fatal error parsing LSan trace (Index mismatch, got index %s but expected %s)" %
                                   (index, expectedIndex))

            component = None
            if len(parts) > 2:
                if parts[2] == "in":
                    component = " ".join(parts[3:-1])
                else:
                    # Remove parentheses around component
                    component = parts[2][1:-1]
            else:
                print("Warning: Missing component in this line: %s" % traceLine, file=sys.stderr)
                component = "<missing>"

            self.backtrace.append(CrashInfo.sanitizeStackFrame(component))
            expectedIndex += 1

        if not self.backtrace and lsanPatternSeen:
            # We've seen the crash address but no frames, so this is likely
            # a crash on the heap with no symbols available. Add one artificial
            # frame so it doesn't show up as "No crash detected"
            self.backtrace.append("??")

    def createShortSignature(self):
        '''
        @rtype: String
        @return: A string representing this crash (short signature)
        '''
        # Try to find the LSan message on stderr and use that as short signature
        abortMsg = AssertionHelper.getAuxiliaryAbortMessage(self.rawStderr)

        # See if we have it in our crash data maybe instead
        if not abortMsg and self.rawCrashData:
            abortMsg = AssertionHelper.getAuxiliaryAbortMessage(self.rawCrashData)

        if abortMsg is not None:
            if isinstance(abortMsg, list):
                return "LeakSanitizer: %s" % " ".join(abortMsg)
            return "LeakSanitizer: %s" % abortMsg

        if not self.backtrace:
            return "No crash detected"

        return "LeakSanitizer: [@ %s]" % self.backtrace[0]


class UBSanCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if crashData is not None:
            self.rawCrashData.extend(crashData)

        self.configuration = configuration

        # If crashData is given, use that to find the UBSan trace, otherwise use stderr
        ubsanOutput = crashData if crashData else stderr
        ubsanErrorPattern = r":\d+:\d+:\s+runtime\s+error:\s+"
        ubsanPatternSeen = False

        expectedIndex = 0
        for traceLine in ubsanOutput:
            if not ubsanPatternSeen:
                if re.search(ubsanErrorPattern, traceLine) is not None:
                    ubsanPatternSeen = True
                continue

            parts = traceLine.strip().split()

            # We only want stack frames
            if not parts or not parts[0].startswith("#"):
                continue

            index = int(parts[0][1:])

            if expectedIndex != index:
                raise RuntimeError("Fatal error parsing UBSan trace (Index mismatch, got index %s but expected %s)" %
                                   (index, expectedIndex))

            component = None
            if len(parts) > 2:
                if parts[2] == "in":
                    component = " ".join(parts[3:-1])
                else:
                    # Remove parentheses around component
                    component = parts[2][1:-1]
            else:
                print("Warning: Missing component in this line: %s" % traceLine, file=sys.stderr)
                component = "<missing>"

            self.backtrace.append(CrashInfo.sanitizeStackFrame(component))
            expectedIndex += 1

        if not self.backtrace and ubsanPatternSeen:
            # We've seen the crash address but no frames, so this is likely
            # a crash on the heap with no symbols available. Add one artificial
            # frame so it doesn't show up as "No crash detected"
            self.backtrace.append("??")

    def createShortSignature(self):
        '''
        @rtype: String
        @return: A string representing this crash (short signature)
        '''
        # Try to find the UBSan message on stderr and use that as short signature
        abortMsg = AssertionHelper.getAuxiliaryAbortMessage(self.rawStderr)

        # See if we have it in our crash data maybe instead
        if not abortMsg and self.rawCrashData:
            abortMsg = AssertionHelper.getAuxiliaryAbortMessage(self.rawCrashData)

        if abortMsg is not None:
            if isinstance(abortMsg, list):
                return "UndefinedBehaviorSanitizer: %s" % " ".join(abortMsg)
            return "UndefinedBehaviorSanitizer: %s" % abortMsg

        if not self.backtrace:
            return "No crash detected"

        return "UndefinedBehaviorSanitizer: [@ %s]" % self.backtrace[0]


class GDBCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if crashData is not None:
            self.rawCrashData.extend(crashData)

        self.configuration = configuration

        # If crashData is given, use that to find the GDB trace, otherwise use stderr
        if crashData:
            gdbOutput = crashData
        else:
            gdbOutput = stderr

        gdbFramePatterns = [
            "\\s*#(\\d+)\\s+(0x[0-9a-f]+) in (.+?) \\(.*?\\)( at .+)?",
            "\\s*#(\\d+)\\s+()(.+?) \\(.*?\\)( at .+)?",
            "\\s*#(\\d+)\\s+()(<signal handler called>)"
        ]

        gdbRegisterPattern = RegisterHelper.getRegisterPattern() + "\\s+0x([0-9a-f]+)"
        gdbCrashAddressPattern = "Crash Address:\\s+0x([0-9a-f]+)"
        gdbCrashInstructionPattern = "=> 0x[0-9a-f]+(?: <.+>)?:\\s+(.*)"

        lastLineBuf = ""

        pastFrames = False

        for traceLine in gdbOutput:
            # Do a very simple check for a frame number in combination with pending
            # buffer content. If we detect this constellation, then it's highly likely
            # that we have a valid trace line but no pattern that fits it. We need
            # to make sure that we report this.
            if (not pastFrames and re.match("\\s*#\\d+.+", lastLineBuf) is not None and
                    re.match("\\s*#\\d+.+", traceLine) is not None):
                print("Fatal error parsing this GDB trace line:", file=sys.stderr)
                print(lastLineBuf, file=sys.stderr)
                raise RuntimeError("Fatal error parsing GDB trace")

            if not lastLineBuf:
                match = re.search(gdbRegisterPattern, traceLine)
                if match is not None:
                    pastFrames = True
                    register = match.group(1)
                    value = int(match.group(2), 16)
                    self.registers[register] = value
                else:
                    match = re.search(gdbCrashAddressPattern, traceLine)
                    if match is not None:
                        self.crashAddress = int(match.group(1), 16)
                    else:
                        match = re.search(gdbCrashInstructionPattern, traceLine)
                        if match is not None:
                            self.crashInstruction = match.group(1)

                            # In certain cases, the crash instruction can have
                            # trailing function information, strip it here.
                            match = re.search("(\\s+<.+>\\s*)$", self.crashInstruction)
                            if match is not None:
                                self.crashInstruction = self.crashInstruction.replace(match.group(1), "")

            if not pastFrames:
                if not lastLineBuf and re.match("\\s*#\\d+.+", traceLine) is None:
                    # Skip additional lines
                    continue

                lastLineBuf += traceLine

                functionName = None
                frameIndex = None
                gdbDebugInfoMismatch = False

                for gdbPattern in gdbFramePatterns:
                    match = re.search(gdbPattern, lastLineBuf)
                    if match is not None:
                        frameIndex = int(match.group(1))
                        functionName = match.group(3)

                        # When GDB runs into unknown types in debug info (e.g. due to version mismatch),
                        # then it emits an additional signature segment that we need to remove later.
                        gdbDebugInfoMismatch = ("unknown type in" in lastLineBuf and "CU 0x" in lastLineBuf)
                        break

                if frameIndex is None:
                    # Line might not be complete yet, try adding the next
                    continue
                else:
                    # Successfully parsed line, reset last line buffer
                    lastLineBuf = ""

                # Allow #0 to appear twice in the beginning, GDB does this for core dumps ...
                if len(self.backtrace) != frameIndex and frameIndex == 0:
                    self.backtrace.pop(0)
                elif len(self.backtrace) != frameIndex:
                    print("Fatal error parsing this GDB trace (Index mismatch, wanted %s got %s ): " %
                          (len(self.backtrace), frameIndex), file=sys.stderr)
                    print(os.linesep.join(gdbOutput), file=sys.stderr)
                    raise RuntimeError("Fatal error parsing GDB trace")

                # This is a workaround for GDB throwing an error while resolving function arguments
                # in the trace and aborting. We try to remove the error message to at least recover
                # the function name properly.
                gdbErrorIdx = functionName.find(" (/build/buildd/gdb")
                if gdbErrorIdx > 0:
                    functionName = functionName[:gdbErrorIdx]

                if gdbDebugInfoMismatch:
                    # Remove addtional signature segment
                    functionName = CrashInfo.sanitizeStackFrame(functionName)

                self.backtrace.append(functionName)

        if self.crashInstruction is not None:
            # Remove any leading/trailing whitespaces
            self.crashInstruction = self.crashInstruction.strip()

        # If we have no crash address but the instruction, try to calculate the crash address
        if self.crashAddress is None and self.crashInstruction is not None:
            crashAddress = GDBCrashInfo.calculateCrashAddress(self.crashInstruction, self.registers)

            if isinstance(crashAddress, (six.text_type, bytes)):
                self.failureReason = crashAddress
                return

            self.crashAddress = crashAddress

            if self.crashAddress is not None and self.crashAddress < 0:
                if RegisterHelper.getBitWidth(self.registers) == 32:
                    self.crashAddress = uint32(self.crashAddress)
                else:
                    # Assume 64 bit width
                    self.crashAddress = uint64(self.crashAddress)

    @staticmethod
    def calculateCrashAddress(crashInstruction, registerMap):
        '''
        Calculate the crash address given the crash instruction and register contents

        @type crashInstruction: string
        @param crashInstruction: Crash instruction string as provided by GDB
        @type registerMap: Map from string to int
        @param registerMap: Map of register names to values

        @rtype: int
        @return The calculated crash address

        On error, a string containing the failure message is returned instead.
        '''

        if not crashInstruction:
            # GDB shows us no instruction, so the memory at the instruction
            # pointer address must be inaccessible and we should assume
            # that this caused our crash.
            return RegisterHelper.getInstructionPointer(registerMap)

        parts = crashInstruction.split(None, 1)

        if len(parts) == 1:
            # Single instruction without any operands?
            # Only accept those that we explicitly know so far.

            instruction = parts[0]

            if instruction == "ret" or instruction == "retq":
                # If ret is crashing, it's most likely due to the stack pointer
                # pointing somewhere where it shouldn't point, so use that as
                # the crash address.
                return RegisterHelper.getStackPointer(registerMap)
            elif instruction == "ud2" or instruction == "(bad)":
                # ud2 - Raise invalid opcode exception
                # We treat this like invalid instruction
                #
                # (bad) - Assembly at the instruction pointer is not valid
                # We also consider this an invalid instruction
                return RegisterHelper.getInstructionPointer(registerMap)
            else:
                raise RuntimeError("Unsupported non-operand instruction: %s" % instruction)

        if len(parts) != 2:
            raise RuntimeError("Failed to split instruction and operands apart: %s" % crashInstruction)

        instruction = parts[0]
        operands = parts[1]

        if not re.match("[a-z\\.]+", instruction):
            raise RuntimeError("Invalid instruction: %s" % instruction)

        parts = operands.split(",")

        # We now have four possibilities:
        # 1. Length of parts is 1, that means we have one operand
        # 2. Length of parts is 2, that means we have two simple operands
        # 3. Length of parts is 4 and
        #  a) First part contains '(' but not ')', meaning the first operand is complex
        #  b) First part contains no '(' or ')', meaning the last operand is complex
        #    e.g. mov    %ecx,0x500094(%r15,%rdx,4)
        #
        #  4. Length of parts is 3, just one complex operand.
        #   e.g. shrb   -0x69(%rdx,%rbx,8)

        # When we fail, try storing a reason here
        failureReason = "Unknown failure."

        def isDerefOp(op):
            return "(" in op and ")" in op

        def calculateDerefOpAddress(derefOp):
            match = re.match("\\*?((?:\\-?0x[0-9a-f]+)?)\\(%([a-z0-9]+)\\)", derefOp)
            if match is not None:
                offset = 0
                if match.group(1):
                    offset = int(match.group(1), 16)

                val = RegisterHelper.getRegisterValue(match.group(2), registerMap)

                # If we don't have the value, return None
                if val is None:
                    return (None, "Missing value for register %s " % match.group(2))
                else:
                    if RegisterHelper.getBitWidth(registerMap) == 32:
                        return (int32(uint32(offset) + uint32(val)), None)
                    else:
                        # Assume 64 bit width
                        return (int64(uint64(offset) + uint64(val)), None)
            else:
                return (None, "Failed to match dereference operation.")

        if RegisterHelper.isX86Compatible(registerMap):
            if len(parts) == 1:
                if re.match("(push|pop|call)(l|w|q)?$", instruction):
                    # push/pop/call are quite special because they can perform an optional
                    # memory dereference before touching the stack. We don't know for sure
                    # which of the two operations fail if we detect a deref in the instruction,
                    # but for now we assume that the deref fails and the stack pointer is ok.
                    #
                    # TODO: Fix this properly by including readability information in GDB output
                    if isDerefOp(parts[0]):
                        (val, failed) = calculateDerefOpAddress(parts[0])
                        if failed:
                            failureReason = failed
                        else:
                            return val
                    else:
                        # No deref, so the stack access must be failing
                        return RegisterHelper.getStackPointer(registerMap)
                else:
                    if isDerefOp(parts[0]):
                        # Single operand instruction with a memory dereference
                        # We list supported ones explicitly to make sure that
                        # we don't mix them with instructions that also
                        # interacts with the stack pointer.
                        if instruction.startswith("set"):
                            (val, failed) = calculateDerefOpAddress(parts[0])
                            if failed:
                                failureReason = failed
                            else:
                                return val
                    else:
                        failureReason = "Unsupported single-operand instruction."
            elif len(parts) == 2:
                failureReason = "Unknown failure with two-operand instruction."
                derefOp = None
                if isDerefOp(parts[0]):
                    derefOp = parts[0]

                if isDerefOp(parts[1]):
                    if derefOp is not None:
                        if ":(" in parts[1]:
                            # This can be an instruction using multiple segments, like:
                            #
                            #   movsq  %ds:(%rsi),%es:(%rdi)
                            #
                            #  (gdb) p $_siginfo._sifields._sigfault.si_addr
                            #    $1 = (void *) 0x7ff846e64d28
                            #    (gdb) x /i $pc
                            #    => 0x876b40 <js::ArgumentsObject::create<CopyFrameArgs>(JSContext*, JS::HandleScript, JS::HandleFunction, unsigned int, CopyFrameArgs&)+528>:   movsq  %ds:(%rsi),%es:(%rdi)  # noqa
                            #    (gdb) info reg $ds
                            #    ds             0x0      0
                            #    (gdb) info reg $es
                            #    es             0x0      0
                            #    (gdb) info reg $rsi
                            #    rsi            0x7ff846e64d28   140704318115112
                            #    (gdb) info reg $rdi
                            #    rdi            0x7fff27fac030   140733864132656
                            #
                            #
                            # We don't support this right now, so return None.
                            #
                            return None

                        raise RuntimeError("Instruction operands have multiple loads? %s" % crashInstruction)

                    derefOp = parts[1]

                if derefOp is not None:
                    (val, failed) = calculateDerefOpAddress(derefOp)
                    if failed:
                        failureReason = failed
                    else:
                        return val
                else:
                    failureReason = ("Failed to decode two-operand instruction: No dereference operation or "
                                     "hardcoded address detected.")
                    # We might still be reading from/writing to a hardcoded address.
                    # Note that it's not possible to have two hardcoded addresses
                    # in one instruction, one operand must be a register or immediate
                    # constant (denoted by leading $). In some cases, like a movabs
                    # instruction, the immediate constant however is dereferenced
                    # and is the first operator. So we first check parts[1] then
                    # parts[0] in case it's a dereferencing operation.

                    for x in (parts[1], parts[0]):
                        result = re.match("\\$?(\\-?0x[0-9a-f]+)", x)
                        if result is not None:
                            return int(result.group(1), 16)
            elif len(parts) == 3:
                # Example instruction: shrb   -0x69(%rdx,%rbx,8)
                if "(" in parts[0] and ")" in parts[2]:
                    complexDerefOp = parts[0] + "," + parts[1] + "," + parts[2]

                    (result, reason) = GDBCrashInfo.calculateComplexDerefOpAddress(complexDerefOp, registerMap)

                    if result is None:
                        failureReason = reason
                    else:
                        return result
                else:
                    raise RuntimeError("Unexpected instruction pattern: %s" % crashInstruction)
            elif len(parts) == 4:
                if "(" in parts[0] and ")" not in parts[0]:
                    complexDerefOp = parts[0] + "," + parts[1] + "," + parts[2]
                elif "(" not in parts[0] and ")" not in parts[0]:
                    complexDerefOp = parts[1] + "," + parts[2] + "," + parts[3]

                (result, reason) = GDBCrashInfo.calculateComplexDerefOpAddress(complexDerefOp, registerMap)

                if result is None:
                    failureReason = reason
                else:
                    return result
            else:
                raise RuntimeError("Unexpected length after splitting operands of this instruction: %s" %
                                   crashInstruction)

        if RegisterHelper.isARMCompatible(registerMap):
            # Anything that is not explicitly handled now is considered unsupported
            failureReason = "Unsupported instruction in incomplete ARM/ARM64 support."

            def getARMImmConst(val):
                val = val.replace("#", "").strip()
                if val.startswith("0x"):
                    return int(val, 16)
                return int(val)

            def calculateARMDerefOpAddress(derefOp):
                derefOps = derefOp.split(",")

                if len(derefOps) > 2:
                    return (None, "More than two deref operands found.")

                offset = 0

                if len(derefOps) == 2:
                    offset = getARMImmConst(derefOps[1])

                val = RegisterHelper.getRegisterValue(derefOps[0], registerMap)

                # If we don't have the value, return None
                if val is None:
                    return (None, "Missing value for register %s " % derefOps[0])
                else:
                    if RegisterHelper.getBitWidth(registerMap) == 32:
                        return (int32(uint32(offset) + uint32(val)), None)
                    else:
                        # Assume 64 bit width
                        return (int64(uint64(offset) + uint64(val)), None)

            # ARM assembly has nested comma-separated operands, so we need to merge
            # those inside  brackets back together before proceeding.
            for i in range(0, len(parts)):
                if i >= len(parts):
                    break
                if "[" in parts[i] and "]" not in parts[i]:
                    if i + 1 < len(parts):
                        if "]" in parts[i + 1] and "[" not in parts[i + 1]:
                            parts[i] += ", " + parts[i + 1]
                            del parts[i + 1]

            if len(parts) == 1:
                if instruction == ".inst" and parts[0].endswith("; undefined"):
                    # This is an instruction that the dissassembler can't read, so likely a SIGILL
                    return RegisterHelper.getInstructionPointer(registerMap)
            elif len(parts) == 2:
                if instruction.startswith("ldr") or instruction.startswith("str"):
                    # Load/Store instruction
                    match = re.match("^\\s*\\[(.*)\\]$", parts[1])
                    if match is not None:
                        (result, reason) = calculateARMDerefOpAddress(match.group(1))
                        if result is None:
                            failureReason += " (%s)" % reason
                        else:
                            return result
        else:
            failureReason = "Architecture is not supported."

        print("Unable to calculate crash address from instruction: >%s<" % crashInstruction, file=sys.stderr)
        print("Reason: %s" % failureReason, file=sys.stderr)
        return failureReason

    @staticmethod
    def calculateComplexDerefOpAddress(complexDerefOp, registerMap):

        match = re.match("((?:\\-?0x[0-9a-f]+)?)\\(%([a-z0-9]+),%([a-z0-9]+),([0-9]+)\\)", complexDerefOp)
        if match is not None:
            offset = 0
            if match.group(1):
                offset = int(match.group(1), 16)

            regA = RegisterHelper.getRegisterValue(match.group(2), registerMap)
            regB = RegisterHelper.getRegisterValue(match.group(3), registerMap)

            mult = int(match.group(4), 16)

            # If we're missing any of the two register values, return None
            if regA is None or regB is None:
                if regA is None:
                    return (None, "Missing value for register %s" % match.group(2))
                else:
                    return (None, "Missing value for register %s" % match.group(3))

            if RegisterHelper.getBitWidth(registerMap) == 32:
                val = int32(uint32(regA) + uint32(offset) + uint32(regB) * uint32(mult))
            else:
                # Assume 64 bit width
                val = int64(uint64(regA) + uint64(offset) + uint64(regB) * uint64(mult))
            return (int(val), None)

        return (None, "Unknown failure.")


class MinidumpCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if crashData is not None:
            self.rawCrashData.extend(crashData)

        self.configuration = configuration

        # If crashData is given, use that to find the Minidump trace, otherwise use stderr
        if crashData:
            minidumpOuput = crashData
        else:
            minidumpOuput = stderr

        crashThread = None
        for traceLine in minidumpOuput:
            if crashThread is not None:
                if traceLine.startswith("%s|" % crashThread):
                    components = traceLine.split("|")

                    if not components[3]:
                        # If we have no symbols, but we have a library/component, using that allows
                        # us to match on the libary name in the stack which is helpful for crashes
                        # in low level libraries.
                        if components[2]:
                            frame = components[2]
                            if len(components) >= 7 and components[6]:
                                frame = "%s+%s" % (frame, components[6])
                            self.backtrace.append(CrashInfo.sanitizeStackFrame(frame))
                        else:
                            self.backtrace.append("??")
                    else:
                        self.backtrace.append(CrashInfo.sanitizeStackFrame(components[3]))
            elif traceLine.startswith("Crash|"):
                components = traceLine.split("|")
                crashThread = int(components[3])
                self.crashAddress = int(components[2], 16)


class AppleCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if crashData is not None:
            self.rawCrashData.extend(crashData)

        self.configuration = configuration

        inCrashingThread = False
        for line in crashData:
            # Crash address
            if line.startswith("Exception Codes:"):
                # Example:
                #     Exception Type:        EXC_BAD_ACCESS (SIGABRT)
                #     Exception Codes:       KERN_INVALID_ADDRESS at 0x00000001374b893e
                address = line.split(" ")[-1]
                if address.startswith('0x'):
                    self.crashAddress = int(address, 16)

            # Start of stack for crashing thread
            if re.match(r'Thread \d+ Crashed:', line):
                inCrashingThread = True
                continue

            if line.strip() == "":
                inCrashingThread = False
                continue

            if inCrashingThread:
                # Example:
                # 0   js-dbg-64-dm-darwin-a523d4c7efe2    0x00000001004b04c4 js::jit::MacroAssembler::Pop(js::jit::Register) + 180 (MacroAssembler-inl.h:50)  # noqa
                components = line.split(None, 3)
                stackEntry = components[3]
                if stackEntry.startswith('0'):
                    self.backtrace.append("??")
                else:
                    stackEntry = AppleCrashInfo.removeFilename(stackEntry)
                    stackEntry = AppleCrashInfo.removeOffset(stackEntry)
                    stackEntry = CrashInfo.sanitizeStackFrame(stackEntry)
                    self.backtrace.append(stackEntry)

    @staticmethod
    def removeFilename(stackEntry):
        match = re.match(r'(.*) \(\S+\)', stackEntry)
        if match:
            return match.group(1)
        return stackEntry

    @staticmethod
    def removeOffset(stackEntry):
        match = re.match(r'(.*) \+ \d+', stackEntry)
        if match:
            return match.group(1)
        return stackEntry


class CDBCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if crashData is not None:
            self.rawCrashData.extend(crashData)

        self.configuration = configuration

        cdbRegisterPattern = RegisterHelper.getRegisterPattern() + "=([0-9a-f]+)"

        address = ""
        inCrashingThread = False
        inCrashInstruction = False
        inEcxrData = False
        ecxrData = []
        cInstruction = ""

        for line in crashData:
            # Start of .ecxr data
            if re.match(r'0:000> \.ecxr', line):
                inEcxrData = True
                continue

            if inEcxrData:
                # 32-bit example:
                #     0:000> .ecxr
                #     eax=02efff01 ebx=016fddb8 ecx=2b2b2b2b edx=016fe490 esi=02e00310 edi=02e00310
                #     eip=00404c59 esp=016fdc2c ebp=016fddb8 iopl=0         nv up ei pl nz na po nc
                #     cs=0023  ss=002b  ds=002b  es=002b  fs=0053  gs=002b             efl=00010202
                # 64-bit example:
                #     0:000> .ecxr
                #     rax=00007ff74d8fee30 rbx=00000285ef400420 rcx=2b2b2b2b2b2b2b2b
                #     rdx=00000285ef21b940 rsi=000000e87fbfc340 rdi=00000285ef400420
                #     rip=00007ff74d469ff3 rsp=000000e87fbfc040 rbp=fffe000000000000
                #      r8=000000e87fbfc140  r9=000000000001fffc r10=0000000000000649
                #     r11=00000285ef25a000 r12=00007ff74d9239a0 r13=fffa7fffffffffff
                #     r14=000000e87fbfd0e0 r15=0000000000000003
                #     iopl=0         nv up ei pl nz na pe nc
                #     cs=0033  ss=002b  ds=002b  es=002b  fs=0053  gs=002b             efl=00010200
                if line.startswith("cs="):
                    inEcxrData = False
                    continue

                # Crash address
                # Extract the eip/rip specifically for use later
                if "eip=" in line:
                    address = line.split("eip=")[1].split()[0]
                    self.crashAddress = int(address, 16)
                elif "rip=" in line:
                    address = line.split("rip=")[1].split()[0]
                    self.crashAddress = int(address, 16)

                # First extract the line
                # 32-bit example:
                #     eax=02efff01 ebx=016fddb8 ecx=2b2b2b2b edx=016fe490 esi=02e00310 edi=02e00310
                # 64-bit example:
                #     rax=00007ff74d8fee30 rbx=00000285ef400420 rcx=2b2b2b2b2b2b2b2b
                matchLine = re.search(RegisterHelper.getRegisterPattern(), line)
                if matchLine is not None:
                    ecxrData.extend(line.split())

                # Next, put the eax/rax, ebx/rbx, etc. entries into a list of their own, then iterate
                match = re.search(cdbRegisterPattern, line)
                for instr in ecxrData:
                    match = re.search(cdbRegisterPattern, instr)
                    if match is not None:
                        register = match.group(1)
                        value = int(match.group(2), 16)
                        self.registers[register] = value

            # Crash instruction
            # Start of crash instruction details
            if line.startswith("FAULTING_IP"):
                inCrashInstruction = True
                continue

            if inCrashInstruction and not cInstruction:
                if "PROCESS_NAME" in line:
                    inCrashInstruction = False
                    continue

                # 64-bit binaries have a backtick in their addresses, e.g. 00007ff7`1e424e62
                lineWithoutBacktick = line.replace("`", "", 1)
                if address and lineWithoutBacktick.startswith(address):
                    # 32-bit examples:
                    #     25d80b01 cc              int     3
                    #     00404c59 8b39            mov     edi,dword ptr [ecx]
                    # 64-bit example:
                    #     00007ff7`4d469ff3 4c8b01          mov     r8,qword ptr [rcx]
                    cInstruction = line.split(None, 2)[-1]
                    # There may be multiple spaces inside the faulting instruction
                    cInstruction = " ".join(cInstruction.split())
                    self.crashInstruction = cInstruction

            # Start of stack for crashing thread
            if line.startswith("STACK_TEXT:"):
                inCrashingThread = True
                continue

            if inCrashingThread:
                # 32-bit example:
                #     016fdc38 004b2387 01e104e8 016fe490 016fe490 js_32_dm_windows_62f79d676e0e!JSObject::allocKindForTenure+0x9  # noqa
                # 64-bit example:
                #     000000e8`7fbfc040 00007ff7`4d53a984 : 000000e8`7fbfc2c0 00000285`ef7bb400 00000285`ef21b000 00007ff7`4d4254b9 : js_64_dm_windows_62f79d676e0e!JSObject::allocKindForTenure+0x13  # noqa
                if "STACK_COMMAND" in line or "SYMBOL_NAME" in line \
                        or "THREAD_SHA1_HASH_MOD_FUNC" in line or "FAULTING_SOURCE_CODE" in line:
                    inCrashingThread = False
                    continue

                # Ignore cdb error and empty lines
                if "Following frames may be wrong." in line or line.strip() == '':
                    continue

                stackEntry = CDBCrashInfo.removeFilenameAndOffset(line)
                stackEntry = CrashInfo.sanitizeStackFrame(stackEntry)
                self.backtrace.append(stackEntry)

    @staticmethod
    def removeFilenameAndOffset(stackEntry):
        # Extract only the function name
        if "0x" in stackEntry:
            result = stackEntry.split("!")[-1].split("+")[0].split("<")[0].split(" ")[-1]
            if "0x" in result:
                result = "??"  # Sometimes there is only a memory address in the stack
            elif ".exe" in result:
                # Sometimes the binary name is present:
                #     e.g.: "00000000 00000000 unknown!js-dbg-32-prof-dm-windows-42c95d88aaaa.exe+0x0"
                result = "??"
        else:
            result = "??"
        return result


class RustCrashInfo(CrashInfo):

    RE_FRAME = re.compile(r"^( +\d+:( +0x[0-9a-f]+ -)? (?P<symbol>.+?)"
                          r"(::h[0-9a-f]{16})?|\s+at ([A-Za-z]:)?(/[A-Za-z0-9_ .]+)+:\d+)$")

    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if crashData is not None:
            self.rawCrashData.extend(crashData)

        self.configuration = configuration

        # If crashData is given, use that to find the rust backtrace, otherwise use stderr
        rustOutput = crashData or stderr

        self.crashAddress = 0  # this is always an assertion, set to 0 to make matching more efficient

        inAssertion = False
        inBacktrace = False
        for line in rustOutput:
            # Start of stack
            if not inAssertion:
                if AssertionHelper.RE_RUST_ASSERT.match(line) is not None:
                    inAssertion = True
                continue

            frame = self.RE_FRAME.match(line)
            if frame is None and inBacktrace:
                break
            elif frame is not None:
                inBacktrace = True
                if frame.group("symbol"):
                    self.backtrace.append(frame.group("symbol"))


class TSanCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if crashData is not None:
            self.rawCrashData.extend(crashData)

        self.configuration = configuration

        # If crashData is given, use that to find the ASan trace, otherwise use stderr
        tsanOutput = crashData if crashData else stderr

        tsanWarningPattern = r"""WARNING: ThreadSanitizer:.*\s.+?\s+\(pid=\d+\)"""  # noqa

        # Cache this for use by createShortSignature
        self.tsanWarnLine = None
        self.tsanIndexZero = []

        expectedIndex = 0
        reportFound = False
        brokenStack = False
        isDataRace = False
        backtraces = []
        currentBacktrace = None
        for traceLine in tsanOutput:
            if not reportFound:
                match = re.search(tsanWarningPattern, traceLine)
                if match is not None:
                    self.tsanWarnLine = traceLine.strip()
                    reportFound = True
                    isDataRace = "data race" in self.tsanWarnLine
                continue

            if "[failed to restore the stack]" in traceLine:
                # TSan failed to symbolize at least one stack
                brokenStack = True

            parts = traceLine.strip().split()

            # We only want stack frames
            if not parts or not parts[0].startswith("#"):
                continue

            try:
                index = int(parts[0][1:])
            except ValueError:
                continue

            # We may see multiple traces in TSAN
            if index == 0:
                if currentBacktrace is not None:
                    backtraces.append(currentBacktrace)
                currentBacktrace = []
                expectedIndex = 0

            if not expectedIndex == index:
                raise RuntimeError("Fatal error parsing TSan trace (Index mismatch, got index %s but expected %s)" %
                                   (index, expectedIndex))

            component = None
            if len(parts) > 2:
                # TSan has a different trace style than other sanitizers:
                #   TSan uses:
                #     #0 function name filename:line:col (bin+0xaddr)
                #   ASan uses:
                #     #0 0xaddr in function name filename:line
                component = " ".join(parts[1:-2])

                if component == "<null>" and len(parts) > 3:
                    # TSan uses <null> <null> to indicate missing symbols, e.g.
                    #   #1 <null> <null> (libXext.so.6+0xcc89)
                    # Remove parentheses around component
                    component = parts[3][1:-1]
            else:
                print("Warning: Missing component in this line: %s" % traceLine, file=sys.stderr)
                component = "<missing>"

            currentBacktrace.append(CrashInfo.sanitizeStackFrame(component))

            expectedIndex += 1

        if currentBacktrace is not None:
            backtraces.append(currentBacktrace)

        # For data races, TSan emits two stacks. If both stacks are intact,
        # we should try to canonicalize their order to avoid creating multiple
        # buckets for the same race.
        if not brokenStack and isDataRace and len(backtraces) >= 2:
            backtraces = sorted(backtraces[:2]) + backtraces[2:]

        # Merge individual backtraces into one
        for backtrace in backtraces:
            # Memorize index 0 components for short signature later
            self.tsanIndexZero.append(backtrace[0])
            self.backtrace.extend(backtrace)

    def createShortSignature(self):
        '''
        @rtype: String
        @return: A string representing this crash (short signature)
        '''
        if self.tsanWarnLine:
            msg = re.sub(r"\s*\(pid=\d+\)", "", self.tsanWarnLine)
            msg = msg.replace("WARNING: ", "")

            if "data race" in msg or "race on external object" in msg:
                if self.tsanIndexZero:
                    msg += " [@ %s]" % self.tsanIndexZero[0]
                    if len(self.tsanIndexZero) > 1:
                        msg += " vs. [@ %s]" % self.tsanIndexZero[1]
            elif "thread leak" in msg:
                if self.tsanIndexZero:
                    msg += " [@ %s]" % self.tsanIndexZero[0]
            elif "mutex" in msg or "deadlock" in msg:
                for frame in self.backtrace:
                    # This is a heuristic for finding an interesting frame
                    # that does not refer to a mutex primitive.
                    if "mutex" not in frame:
                        msg += " [@ %s]" % frame
                        break
            elif "signal" in msg or "use-after-free" in msg:
                if self.backtrace:
                    msg += " [@ %s]" % self.backtrace[0]
            else:
                raise RuntimeError("Fatal error: TSan trace warning line has unhandled message case: %s" % msg)

            return msg

        return "No TSan warning detected"


class ValgrindCrashInfo(CrashInfo):
    MSG_REGEX = re.compile(r"""
        ==\d+==\s+(?P<msg>
        (\d+(,\d+)*\sbytes\sin\s\d+(,\d+)*\sblocks\sare\s\w+\slost)|
        (Argument\s'\w+'\sof\sfunction\smalloc.+)|
        ((Conditional|Use)\s.+?uninitialised\svalue.+)|
        (Invalid\s\w+\sof\ssize.+)|
        ((Invalid|Mismatched)\sfree\(\).+)|
        (Process\sterminating\swith\sdefault\saction.+)|
        (Source\sand\sdestination\soverlap)|
        (Syscall\sparam.+)
        )""", re.VERBOSE)

    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if crashData is not None:
            self.rawCrashData.extend(crashData)

        self.configuration = configuration

        # If crashData is given, use that to find the Valgrind trace, otherwise use stderr
        vgdOutput = crashData if crashData else stderr
        stackPattern = re.compile(r"""
            ^==\d+==\s+(at|by)\s+            # beginning of entry
            0x[0-9A-Fa-f]+\:\s+              # address
            (?P<func>.+)\s+                  # function name
            \((in\s+)?(?P<file>.+?)(:.+?)?\) # file name
            """, re.VERBOSE)

        foundStart = False
        for traceLine in vgdOutput:
            if not traceLine.startswith("=="):
                # skip unrelated noise
                continue
            elif not foundStart:
                if re.match(self.MSG_REGEX, traceLine) is not None:
                    # skip other lines that are not part of a recognized trace
                    foundStart = True
                # continue search for the beginning of the stack trace
                continue

            lineInfo = re.match(stackPattern, traceLine)
            if lineInfo is not None:
                lineFunc = lineInfo.group("func")
                # if function name is not available use the file name instead
                if lineFunc == "???":
                    lineFunc = lineInfo.group("file")
                self.backtrace.append(CrashInfo.sanitizeStackFrame(lineFunc))

            elif self.backtrace:
                # check if address info is available
                addr = re.match(r"^==\d+==\s+Address\s(?P<addr>0x[0-9A-Fa-f]+)\s", traceLine)
                if addr:
                    self.crashAddress = int(addr.group("addr"), 16)
                # look for '==PID== \n' to indicate the end of a trace
                if re.match(r"^==\d+==\s+$", traceLine) is not None:
                    # done parsing
                    break

    def createShortSignature(self):
        '''
        @rtype: String
        @return: A string representing this crash (short signature)
        '''

        logData = self.rawCrashData if self.rawCrashData else self.rawStderr
        for line in logData:
            m = re.match(ValgrindCrashInfo.MSG_REGEX, line)
            if m and m.group("msg"):
                if self.backtrace:
                    return "Valgrind: %s [@ %s]" % (m.group("msg"), self.backtrace[0])
                return "Valgrind: %s" % m.group("msg")

        if not self.backtrace:
            return "No crash detected"
        return "Valgrind: [@ %s]" % self.backtrace[0]
