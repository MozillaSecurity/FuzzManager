"""
Report Information

Represents information about a report. Specific subclasses implement
different report data supported by the implementation.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""
import json
import os
import re
import sys
import unicodedata
from abc import ABCMeta
from functools import wraps

from FTB import AssertionHelper
from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures import RegisterHelper
from FTB.Signatures.ReportSignature import ReportSignature


def unicode_escape_result(func):
    r"""Decorator to escape control and special block unicode
    characters in a function returning untrusted str values.

    Characters in those blocks are escaped in JS notation (\u{hex})
    """

    class unicode_cc_map:
        def __getitem__(self, char):
            if unicodedata.category(chr(char)) in {"Cc", "So"}:
                return f"\\u{{{char:x}}}"
            raise LookupError()

    @wraps(func)
    def wrapped(*args, **kwds):
        result = func(*args, **kwds)
        return result.translate(unicode_cc_map())

    return wrapped


def _is_unfinished(symbol, operators):
    start, end = operators
    return bool(symbol.count(start) > symbol.count(end))


def uint32(val):
    """Force `val` into unsigned 32-bit range.

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
    """
    return val & 0xFFFFFFFF


def int32(val):
    """Force `val` into signed 32-bit range.

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
    """
    val = uint32(val)
    if val.bit_length() == 32:
        val = val - 0x100000000
    return val


def uint64(val):
    """Force `val` into unsigned 64-bit range.

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
    """
    return val & 0xFFFFFFFFFFFFFFFF


def int64(val):
    """Force `val` into signed 64-bit range.

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
    """
    val = uint64(val)
    if val.bit_length() == 64:
        val = val - 0x10000000000000000
    return val


class TraceParsingError(RuntimeError):
    __slots__ = ("line_no",)

    def __init__(self, *args, **kwds):
        self.line_no = kwds.pop("line_no")
        super().__init__(*args, **kwds)


class ReportInfo(metaclass=ABCMeta):
    """
    Abstract base class that provides a method to instantiate the right sub class.
    It also supports generating a ReportSignature based on the stored information.
    """

    def __init__(self):
        # Store the raw data
        self.rawStdout = []
        self.rawStderr = []
        self.rawReportData = []

        # Store processed data
        self.backtrace = []
        self.registers = {}
        self.reportAddress = None
        self.reportInstruction = None

        # Store configuration data (platform, product, os, etc.)
        self.configuration = None

        # This is an optional testcase that is not stored with the reportInfo but
        # can be "attached" before matching signatures that might require the
        # testcase.
        self.testcase = None

        # This can be used to record failures during signature creation
        self.failureReason = None

    def __str__(self):
        buf = []
        buf.append("Report trace:")
        buf.append("")
        for idx, frame in enumerate(self.backtrace):
            buf.append("# %02d    %s" % (idx, frame))
        buf.append("")

        if self.reportAddress:
            buf.append(f"Report address: 0x{self.reportAddress:x}")

        if self.reportInstruction:
            buf.append(f"Report instruction: {self.reportInstruction}")

        if self.reportAddress or self.reportInstruction:
            buf.append("")

        buf.append("Last 5 lines on stderr:")
        buf.extend(self.rawStderr[-5:])

        return "\n".join(buf)

    def toCacheObject(self):
        """
        Create a cache object for restoring the class instance later on without parsing
        the report data again. This object includes all class fields except for the
        storage heavy raw objects like stdout, stderr and raw reportdata.

        @rtype: dict
        @return: Dictionary containing expensive class fields
        """
        cacheObject = {}
        cacheObject["backtrace"] = self.backtrace
        cacheObject["registers"] = self.registers

        if self.reportAddress is not None:
            cacheObject["reportAddress"] = int(self.reportAddress)
        else:
            cacheObject["reportAddress"] = None

        cacheObject["reportInstruction"] = self.reportInstruction
        cacheObject["failureReason"] = self.failureReason

        return cacheObject

    @staticmethod
    def fromRawReportData(
        stdout, stderr, configuration, auxReportData=None, cacheObject=None
    ):
        """
        Create appropriate ReportInfo instance from raw report data

        @type stdout: List of strings
        @param stdout: List of lines as they appeared on stdout
        @type stderr: List of strings
        @param stderr: List of lines as they appeared on stderr
        @type configuration: ProgramConfiguration
        @param configuration: Exact program configuration that is associated with the
                              report
        @type auxReportData: List of strings
        @param auxReportData: Optional additional report output (e.g. GDB). If not
                             specified, stderr is used.
        @type cacheObject: Dictionary
        @param cacheObject: The cache object that should be used to restore the class
                            fields instead of parsing the report data. The appropriate
                            object can be created by calling the toCacheObject method.

        @rtype: ReportInfo
        @return: Report information object
        """

        assert stdout is None or isinstance(stdout, (list, str, bytes))
        assert stderr is None or isinstance(stderr, (list, str, bytes))
        assert auxReportData is None or isinstance(auxReportData, (list, str, bytes))

        assert isinstance(configuration, ProgramConfiguration)

        if isinstance(stdout, (str, bytes)):
            stdout = stdout.splitlines()

        if isinstance(stderr, (str, bytes)):
            stderr = stderr.splitlines()

        if isinstance(auxReportData, (str, bytes)):
            auxReportData = auxReportData.splitlines()

        if cacheObject is not None:
            c = ReportInfo()

            if stdout is not None:
                c.rawStdout.extend(stdout)

            if stderr is not None:
                c.rawStderr.extend(stderr)

            if auxReportData is not None:
                c.rawReportData.extend(auxReportData)

            c.configuration = configuration
            c.backtrace = cacheObject["backtrace"]
            c.registers = cacheObject["registers"]
            c.reportAddress = cacheObject["reportAddress"]
            c.reportInstruction = cacheObject["reportInstruction"]
            c.failureReason = cacheObject["failureReason"]

            return c

        # some results are weak, meaning any other ReportInfo detected after it will
        # take precedence
        weakResult = None

        asanString = "ERROR: AddressSanitizer"
        asanString2 = "Sanitizer: hard rss limit exhausted"
        gdbString = "received signal SIG"
        gdbCoreString = "Program terminated with signal "
        lsanString = "ERROR: LeakSanitizer:"
        tsanString = "WARNING: ThreadSanitizer:"
        tsanString2 = "ERROR: ThreadSanitizer:"
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

        # Search both reportData and stderr, but prefer reportData
        lines = []
        if auxReportData is not None:
            lines.extend(auxReportData)
        if stderr is not None:
            lines.extend(stderr)

        result = None
        for line in lines:
            if ubsanString in line and re.match(ubsanRegex, line) is not None:
                result = UBSanReportInfo(stdout, stderr, configuration, auxReportData)
                break
            elif (
                asanString in line
                or asanString2 in line
                or ubsanString2 in line
                or tsanString2 in line
            ):
                result = ASanReportInfo(stdout, stderr, configuration, auxReportData)
                break
            elif lsanString in line:
                result = LSanReportInfo(stdout, stderr, configuration, auxReportData)
                break
            elif tsanString in line:
                result = TSanReportInfo(stdout, stderr, configuration, auxReportData)
                break
            elif appleString in line and not line.startswith(minidumpFirstString):
                result = AppleReportInfo(stdout, stderr, configuration, auxReportData)
                break
            elif cdbString in line:
                result = CDBReportInfo(stdout, stderr, configuration, auxReportData)
                break
            elif gdbString in line or gdbCoreString in line:
                result = GDBReportInfo(stdout, stderr, configuration, auxReportData)
                break
            elif not rustFirstDetected and rustFirstString in line:
                rustFirstDetected = True
                minidumpFirstDetected = False
            elif rustFirstDetected and rustSecondString in line:
                weakResult = RustReportInfo(
                    stdout, stderr, configuration, auxReportData
                )
                rustFirstDetected = False
            elif not minidumpFirstDetected and minidumpFirstString in line:
                # Only match Minidump output if the *next* line also contains
                # the second search string defined above.
                rustFirstDetected = False
                minidumpFirstDetected = True
            elif minidumpFirstDetected and minidumpSecondString in line:
                result = MinidumpReportInfo(
                    stdout, stderr, configuration, auxReportData
                )
                break
            elif line.startswith("==") and re.match(ValgrindReportInfo.MSG_REGEX, line):
                result = ValgrindReportInfo(
                    stdout, stderr, configuration, auxReportData
                )
                break
            else:
                minidumpFirstDetected = False

        # Default fallback to be used if there is neither ASan nor GDB output.
        # This is still useful in case there is no report but we want to match
        # e.g. stdout/stderr output with signatures.
        if result is None:
            result = weakResult or NoReportInfo(
                stdout, stderr, configuration, auxReportData
            )

        # Rust symbols have a source hash appended to them. Strip this off regardless of
        # the ReportInfo type
        result.backtrace = [
            re.sub(r"::h[0-9a-f]{16}$", "", frame) for frame in result.backtrace
        ]

        return result

    @unicode_escape_result
    def createShortSignature(self):
        """
        @rtype: String
        @return: A string representing this report (short signature)
        """
        # See if we have an abort message and if so, use that as short signature
        abortMsg = AssertionHelper.getAssertion(self.rawStderr)

        # See if we have an abort message in our report data maybe
        if not abortMsg and self.rawReportData:
            abortMsg = AssertionHelper.getAssertion(self.rawReportData)

        if abortMsg is not None:
            if isinstance(abortMsg, list):
                return " ".join(abortMsg)
            else:
                return abortMsg

        if not self.backtrace:
            return "No report detected"

        return f"[@ {self.backtrace[0]}]"

    def createReportSignature(
        self,
        forceReportAddress=False,
        forceReportInstruction=False,
        maxFrames=8,
        minimumSupportedVersion=13,
    ):
        """
        @param forceReportAddress: If True, the report address will be included in any
                                   case
        @type forceReportAddress: bool
        @param forceReportInstruction: If True, the report instruction will be included
                                       in any case
        @type forceReportInstruction: bool
        @param maxFrames: How many frames (at most) should be included in the signature
        @type maxFrames: int

        @param minimumSupportedVersion: The minimum report signature standard version
                                        that the generated signature should be valid for
                                        (10 => 1.0, 13 => 1.3)
        @type minimumSupportedVersion: int

        @rtype: ReportSignature
        @return: A report signature object
        """
        # Determine the actual number of frames based on how many we got
        if len(self.backtrace) > maxFrames:
            numFrames = maxFrames
        else:
            numFrames = len(self.backtrace)

        symptomArr = []

        # Memorize where we find our abort messages
        abortMsgInReportdata = False

        # See if we have an abort message and if so, get a sanitized version of it
        abortMsgs = AssertionHelper.getAssertion(self.rawStderr)

        if abortMsgs is None and minimumSupportedVersion >= 13:
            # Look for abort messages also inside reportdata
            # only on version 1.3 or higher, because the "reportdata" source
            # type for output matching was added in that version.
            abortMsgs = AssertionHelper.getAssertion(self.rawReportData)
            if abortMsgs is not None:
                abortMsgInReportdata = True

        # Still no abort message, fall back to auxiliary abort messages (ASan/UBSan)
        if abortMsgs is None:
            abortMsgs = AssertionHelper.getAuxiliaryAbortMessage(self.rawStderr)

        if abortMsgs is None and minimumSupportedVersion >= 13:
            # Look for auxiliary abort messages also inside reportdata
            # only on version 1.3 or higher, because the "reportdata" source
            # type for output matching was added in that version.
            abortMsgs = AssertionHelper.getAuxiliaryAbortMessage(self.rawReportData)
            if abortMsgs is not None:
                abortMsgInReportdata = True

        if abortMsgs is not None:
            if not isinstance(abortMsgs, list):
                abortMsgs = [abortMsgs]

            for abortMsg in abortMsgs:
                abortMsg = AssertionHelper.getSanitizedAssertionPattern(abortMsg)
                abortMsgSrc = "stderr"
                if abortMsgInReportdata:
                    abortMsgSrc = "reportdata"

                # Compose StringMatch object with PCRE pattern.
                # Versions below 1.2 only support the full object PCRE style,
                # for anything newer, use the short form with forward slashes
                # to increase the readability of the signatures.
                if minimumSupportedVersion < 12:
                    stringObj = {"value": abortMsg, "matchType": "pcre"}
                    symptomObj = {
                        "type": "output",
                        "src": abortMsgSrc,
                        "value": stringObj,
                    }
                else:
                    symptomObj = {
                        "type": "output",
                        "src": abortMsgSrc,
                        "value": f"/{abortMsg}/",
                    }
                symptomArr.append(symptomObj)

        # Consider the first four frames as top stack
        topStackLimit = 4

        # If we have less than topStackLimit frames available anyway, count the
        # difference between topStackLimit and the available frames already as missing.
        # E.g. if the trace has only three entries anyway, one will be considered
        # missing right from the start. This should prevent that very short stack frames
        # are used for signatures without additional report information that narrows the
        # signature.

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
                    symptomObj = {
                        "type": "stackFrame",
                        "frameNumber": idx,
                        "functionName": functionName,
                    }
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
                if str(framesArray[frameIdx]) != "?":
                    lastSymbolizedFrame = frameIdx

            if lastSymbolizedFrame is not None:
                # Remove all elements behind the last symbolized frame
                framesArray = framesArray[: lastSymbolizedFrame + 1]
            else:
                # We don't have a single symbolized frame, so it doesn't make sense
                # to keep any wildcards in case we added some for unsymbolized frames.
                framesArray = []

            if framesArray:
                symptomArr.append({"type": "stackFrames", "functionNames": framesArray})

        # Missing too much of the top stack frames, add additional report information
        stackIsInsufficient = topStackMissCount >= 2 and abortMsgs is None

        includeReportAddress = stackIsInsufficient or forceReportAddress
        includeReportInstruction = (
            stackIsInsufficient and self.reportInstruction is not None
        ) or forceReportInstruction

        if not symptomArr and not includeReportInstruction:
            # If at this point, we don't have any symptoms from either backtrace
            # or abort messages and we also lack a report instruction, then the
            # the only potential symptom that remains is the report address.
            # That symptom alone would in most cases be too broad for an automatically
            # generated signature, so we stop at this point.
            self.failureReason = "Insufficient data to generate report signature."
            return None

        if includeReportAddress:
            if self.reportAddress is None:
                reportAddress = ""
            elif self.reportAddress < 0x100:
                # Try to match report addresses that are small but non-zero
                # with a generic range that is likely associated with null-deref.
                reportAddress = "< 0x100"
            else:
                reportAddress = "> 0xFF"

            reportAddressSymptomObj = {
                "type": "reportAddress",
                "address": reportAddress,
            }
            symptomArr.append(reportAddressSymptomObj)

        if includeReportInstruction:
            if self.reportInstruction is None:
                failureReason = self.failureReason
                self.failureReason = (
                    "No report instruction available from report data. Reason: "
                    f"{failureReason}"
                )
                return None

            reportInstructionSymptomObj = {
                "type": "instruction",
                "instructionName": self.reportInstruction,
            }
            symptomArr.append(reportInstructionSymptomObj)

        sigObj = {"symptoms": symptomArr}

        return ReportSignature(json.dumps(sigObj, indent=2, sort_keys=True))

    @staticmethod
    def sanitizeStackFrame(frame):
        """
        This function removes function arguments and other non-generic parts
        of the function frame, returning a (hopefully) generic function name.

        @param frame: The stack frame to sanitize
        @type forceReportAddress: str

        @rtype: str
        @return: Sanitized stack frame
        """

        # Remove any trailing const declaration
        if frame.endswith(" const"):
            frame = frame[0 : -len(" const")]

        # Strip the last ( ) segment, which might also contain more parentheses
        if frame.endswith(")"):
            idx = len(frame) - 2
            parlevel = 0
            while idx > 0:
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


class NoReportInfo(ReportInfo):
    def __init__(self, stdout, stderr, configuration, reportData=None):
        """
        Private constructor, called by L{ReportInfo.fromRawReportData}. Do not use
        directly.
        """
        ReportInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if reportData is not None:
            self.rawReportData.extend(reportData)

        self.configuration = configuration


class ASanReportInfo(ReportInfo):
    def __init__(self, stdout, stderr, configuration, reportData=None):
        """
        Private constructor, called by L{ReportInfo.fromRawReportData}. Do not use
        directly.
        """
        ReportInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if reportData is not None:
            self.rawReportData.extend(reportData)

        self.configuration = configuration

        # If reportData is given, use that to find the ASan trace, otherwise use stderr
        asanOutput = reportData if reportData else stderr

        asanReportAddressPattern = r"""(?x)
            [A-Za-z]+Sanitizer.*\s
              (?:on\saddress             # Most common format, used for all overflows
                |on\sunknown\saddress    # Used in case of a SIGSEGV
                |double-free\son         # Used in case of a double-free
                |allocator\sis\sout\sof\smemory\strying\sto\sallocate\s0x[0-9a-f]+\s
                 bytes
                |failed\sto\sallocate\s0x[0-9a-f]+\s
                |negative-size-param:\s*\(size=-\d+\)
                |not\smalloc\(\)-ed:     # Used in case of a wild free
                                         #   (on unallocated memory)
                |not\sowned:             # Used when calling __asan_get_allocated_size()
                                         #   on a pointer that isn't owned
                |\w+-param-overlap:      # Bad memcpy/strcpy/strcat... etc
                |requested\sallocation\ssize\s0x[0-9a-f]+\s
                |soft\srss\slimit\sexhausted
                |hard\srss\slimit\sexhausted)
            (\s*0x([0-9a-f]+))?"""
        asanRegisterPattern = (
            r"(?:\s+|\()pc\s+0x([0-9a-f]+)\s+(sp|bp)\s+0x([0-9a-f]+)\s+(sp|bp)\s+"
            r"0x([0-9a-f]+)"
        )

        expectedIndex = 0
        reportFound = False
        for line_no, traceLine in enumerate(asanOutput):
            if not reportFound or self.reportAddress is None:
                match = re.search(asanReportAddressPattern, traceLine)
                if match is not None:
                    reportFound = True
                    try:
                        self.reportAddress = int(match.group(1), 16)
                    except TypeError:
                        pass  # No report address available

                    # Report Address and Registers are in the same line for ASan
                    match = re.search(asanRegisterPattern, traceLine)
                    # Collect register values if they are available in the ASan trace
                    if match is not None:
                        self.registers["pc"] = int(match.group(1), 16)
                        self.registers[match.group(2)] = int(match.group(3), 16)
                        self.registers[match.group(4)] = int(match.group(5), 16)
                elif not reportFound:
                    # Not in the ASan output yet.
                    # Some lines in eg. debug+asan builds might error if we continue.
                    continue

            index, parts = self.split_frame(traceLine)
            if index is None:
                continue

            # We may see multiple traces in ASAN
            if index == 0:
                expectedIndex = 0

            if not expectedIndex == index:
                raise TraceParsingError(
                    f"Fatal error parsing ASan trace (Index mismatch, got index {index}"
                    f" but expected {expectedIndex})",
                    line_no=line_no,
                )

            component = None
            # TSan doesn't include address, symbol will be immediately following the
            # frame number
            if len(parts) > 1 and not parts[1].startswith("0x"):
                if parts[1] == "<null>":
                    # the last part is either `(lib.so+0xoffset)` or `(0xaddress)`
                    if "+" in parts[-1]:
                        # Remove parentheses around component
                        component = parts[-1][1:-1]
                    else:
                        component = "<missing>"
                else:
                    component = " ".join(parts[1:-2])
            elif len(parts) > 2:
                if parts[2] == "in":
                    component = " ".join(parts[3:-1])
                elif parts[2] == "(<unknown module>)":
                    component = "<missing>"
                else:
                    # Remove parentheses around component
                    component = parts[2][1:-1]
            else:
                print(
                    f"Warning: Missing component in this line: {traceLine}",
                    file=sys.stderr,
                )
                component = "<missing>"

            self.backtrace.append(ReportInfo.sanitizeStackFrame(component))
            expectedIndex += 1

    @staticmethod
    def split_frame(line):
        parts = line.strip().split()

        # We only want stack frames
        if not parts or not parts[0].startswith("#"):
            return None, None

        try:
            frame_no = int(parts[0][1:])
        except ValueError:
            return None, None

        # try to put parts back together which contain spaces contained in () or <>
        idx = 1
        while len(parts) > idx + 1:
            if _is_unfinished(parts[idx], "()") or _is_unfinished(parts[idx], "<>"):
                parts = (
                    parts[:idx] + [f"{parts[idx]} {parts[idx + 1]}"] + parts[idx + 2 :]
                )
            else:
                idx += 1

        # put "const" back with the function signature
        if "const" in parts:
            idx = parts.index("const")
            assert idx > 0
            if parts[idx - 1].endswith(")"):
                parts = (
                    parts[: idx - 1] + [f"{parts[idx - 1]} const"] + parts[idx + 1 :]
                )

        # clang 14 adds BuildId as last segment
        if parts[-1].startswith("(BuildId: "):
            parts.pop()

        return frame_no, parts

    @unicode_escape_result
    def createShortSignature(self):
        """
        @rtype: String
        @return: A string representing this report (short signature)
        """
        # Always prefer using regular program aborts
        abortMsg = AssertionHelper.getAssertion(self.rawStderr)

        # Also check the report data for program abort data
        # (sometimes happens e.g. with MOZ_REPORT)
        if not abortMsg and self.rawReportData:
            abortMsg = AssertionHelper.getAssertion(self.rawReportData)

        if abortMsg is not None:
            if isinstance(abortMsg, list):
                return " ".join(abortMsg)
            else:
                return abortMsg

        # If we don't have a program abort message, see if we have an ASan
        # specific abort message other than a report message that we can use.
        abortMsg = AssertionHelper.getAuxiliaryAbortMessage(self.rawStderr)

        # Also check the report data again
        if not abortMsg and self.rawReportData:
            abortMsg = AssertionHelper.getAuxiliaryAbortMessage(self.rawReportData)

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
            asanMsg = re.sub(
                (
                    r"\[0x[0-9a-f]+,0x[0-9a-f]+\) and \[0x[0-9a-f]+, 0x[0-9a-f]+\) "
                    "overlap$"
                ),
                "overlap",
                asanMsg,
            )
            asanMsg = re.sub(
                r"0x[0-9a-f]+\s\(0x[0-9a-f]+\safter\sadjustments.+?\)\s", "", asanMsg
            )
            asanMsg = re.sub(r"size\sof\s0x[0-9a-f]+$", "size", asanMsg)

            if self.backtrace:
                asanMsg += f" [@ {self.backtrace[0]}]"
            if rwMsg:
                # Strip address and thread
                rwMsg = re.sub(" at 0x[0-9a-f]+ thread .+", "", rwMsg)
                asanMsg += f" with {rwMsg}"

            return asanMsg

        if not self.backtrace:
            if self.reportAddress is not None:
                # We seem to have a report but no backtrace, so let it show up as a
                # report with no symbols
                return "[@ ??]"

            return "No report detected"

        return f"[@ {self.backtrace[0]}]"


class LSanReportInfo(ReportInfo):
    def __init__(self, stdout, stderr, configuration, reportData=None):
        """
        Private constructor, called by L{ReportInfo.fromRawReportData}. Do not use
        directly.
        """
        ReportInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if reportData is not None:
            self.rawReportData.extend(reportData)

        self.configuration = configuration

        # If reportData is given, use that to find the LSan trace, otherwise use stderr
        lsanOutput = reportData if reportData else stderr
        lsanErrorPattern = "ERROR: LeakSanitizer:"
        lsanPatternSeen = False

        expectedIndex = 0
        for line_no, traceLine in enumerate(lsanOutput):
            if not lsanErrorPattern:
                if lsanErrorPattern in traceLine:
                    lsanPatternSeen = True
                continue

            index, parts = ASanReportInfo.split_frame(traceLine)
            if index is None:
                continue

            if expectedIndex != index:
                raise TraceParsingError(
                    f"Fatal error parsing LSan trace (Index mismatch, got index {index}"
                    f" but expected {expectedIndex})",
                    line_no=line_no,
                )

            component = None
            if len(parts) > 2:
                if parts[2] == "in":
                    component = " ".join(parts[3:-1])
                else:
                    # Remove parentheses around component
                    component = parts[2][1:-1]
            else:
                print(
                    f"Warning: Missing component in this line: {traceLine}",
                    file=sys.stderr,
                )
                component = "<missing>"

            self.backtrace.append(ReportInfo.sanitizeStackFrame(component))
            expectedIndex += 1

        if not self.backtrace and lsanPatternSeen:
            # We've seen the report address but no frames, so this is likely
            # a report on the heap with no symbols available. Add one artificial
            # frame so it doesn't show up as "No report detected"
            self.backtrace.append("??")

    @unicode_escape_result
    def createShortSignature(self):
        """
        @rtype: String
        @return: A string representing this report (short signature)
        """
        # Try to find the LSan message on stderr and use that as short signature
        abortMsg = AssertionHelper.getAuxiliaryAbortMessage(self.rawStderr)

        # See if we have it in our report data maybe instead
        if not abortMsg and self.rawReportData:
            abortMsg = AssertionHelper.getAuxiliaryAbortMessage(self.rawReportData)

        if abortMsg is not None:
            if isinstance(abortMsg, list):
                return f"LeakSanitizer: {' '.join(abortMsg)}"
            return f"LeakSanitizer: {abortMsg}"

        if not self.backtrace:
            return "No report detected"

        return f"LeakSanitizer: [@ {self.backtrace[0]}]"


class UBSanReportInfo(ReportInfo):
    def __init__(self, stdout, stderr, configuration, reportData=None):
        """
        Private constructor, called by L{ReportInfo.fromRawReportData}. Do not use
        directly.
        """
        ReportInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if reportData is not None:
            self.rawReportData.extend(reportData)

        self.configuration = configuration

        # If reportData is given, use that to find the UBSan trace, otherwise use stderr
        ubsanOutput = reportData if reportData else stderr
        ubsanErrorPattern = r":\d+:\d+:\s+runtime\s+error:\s+"
        ubsanPatternSeen = False

        expectedIndex = 0
        for line_no, traceLine in enumerate(ubsanOutput):
            if not ubsanPatternSeen:
                if re.search(ubsanErrorPattern, traceLine) is not None:
                    ubsanPatternSeen = True
                continue

            index, parts = ASanReportInfo.split_frame(traceLine)
            if index is None:
                continue

            if expectedIndex != index:
                raise TraceParsingError(
                    f"Fatal error parsing UBSan trace (Index mismatch, got index "
                    f"{index} but expected {expectedIndex})",
                    line_no=line_no,
                )

            component = None
            if len(parts) > 2:
                if parts[2] == "in":
                    component = " ".join(parts[3:-1])
                else:
                    # Remove parentheses around component
                    component = parts[2][1:-1]
            else:
                print(
                    f"Warning: Missing component in this line: {traceLine}",
                    file=sys.stderr,
                )
                component = "<missing>"

            self.backtrace.append(ReportInfo.sanitizeStackFrame(component))
            expectedIndex += 1

    @unicode_escape_result
    def createShortSignature(self):
        """
        @rtype: String
        @return: A string representing this report (short signature)
        """
        # Try to find the UBSan message on stderr and use that as short signature
        abortMsg = AssertionHelper.getAuxiliaryAbortMessage(self.rawStderr)

        # See if we have it in our report data maybe instead
        if not abortMsg and self.rawReportData:
            abortMsg = AssertionHelper.getAuxiliaryAbortMessage(self.rawReportData)

        if abortMsg is not None:
            if isinstance(abortMsg, list):
                return f"UndefinedBehaviorSanitizer: {' '.join(abortMsg)}"
            return f"UndefinedBehaviorSanitizer: {abortMsg}"

        if not self.backtrace:
            return "No report detected"

        return f"UndefinedBehaviorSanitizer: [@ {self.backtrace[0]}]"


class GDBReportInfo(ReportInfo):
    def __init__(self, stdout, stderr, configuration, reportData=None):
        """
        Private constructor, called by L{ReportInfo.fromRawReportData}. Do not use
        directly.
        """
        ReportInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if reportData is not None:
            self.rawReportData.extend(reportData)

        self.configuration = configuration

        # If reportData is given, use that to find the GDB trace, otherwise use stderr
        if reportData:
            gdbOutput = reportData
        else:
            gdbOutput = stderr

        gdbFramePatterns = [
            "\\s*#(\\d+)\\s+(0x[0-9a-f]+) in (.+?) \\(.*?\\)( at .+)?",
            "\\s*#(\\d+)\\s+()(.+?) \\(.*?\\)( at .+)?",
            "\\s*#(\\d+)\\s+()(<signal handler called>)",
        ]

        gdbRegisterPattern = RegisterHelper.getRegisterPattern() + "\\s+0x([0-9a-f]+)"
        gdbReportAddressPattern = "Report Address:\\s+0x([0-9a-f]+)"
        gdbReportInstructionPattern = "=> 0x[0-9a-f]+(?: <.+>)?:\\s+(.*)"

        lastLineBuf = ""

        pastFrames = False

        for line_no, traceLine in enumerate(gdbOutput):
            # Do a very simple check for a frame number in combination with pending
            # buffer content. If we detect this constellation, then it's highly likely
            # that we have a valid trace line but no pattern that fits it. We need
            # to make sure that we report this.
            if (
                not pastFrames
                and re.match("\\s*#\\d+.+", lastLineBuf) is not None
                and re.match("\\s*#\\d+.+", traceLine) is not None
            ):
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
                    match = re.search(gdbReportAddressPattern, traceLine)
                    if match is not None:
                        self.reportAddress = int(match.group(1), 16)
                    else:
                        match = re.search(gdbReportInstructionPattern, traceLine)
                        if match is not None:
                            self.reportInstruction = match.group(1)

                            # In certain cases, the report instruction can have
                            # trailing function information, strip it here.
                            match = re.search("(\\s+<.+>\\s*)$", self.reportInstruction)
                            if match is not None:
                                self.reportInstruction = self.reportInstruction.replace(
                                    match.group(1), ""
                                )

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

                        # When GDB runs into unknown types in debug info (e.g. due to
                        # version mismatch), then it emits an additional signature
                        # segment that we need to remove later.
                        gdbDebugInfoMismatch = (
                            "unknown type in" in lastLineBuf and "CU 0x" in lastLineBuf
                        )
                        break

                if frameIndex is None:
                    # Line might not be complete yet, try adding the next
                    continue
                else:
                    # Successfully parsed line, reset last line buffer
                    lastLineBuf = ""

                # Allow #0 to appear twice in the beginning, GDB does this for core
                # dumps ...
                if len(self.backtrace) != frameIndex and frameIndex == 0:
                    self.backtrace.pop(0)
                elif len(self.backtrace) != frameIndex:
                    print(
                        "Fatal error parsing this GDB trace (Index mismatch, wanted "
                        f"{len(self.backtrace)} got {frameIndex}): ",
                        file=sys.stderr,
                    )
                    print(os.linesep.join(gdbOutput), file=sys.stderr)
                    raise TraceParsingError(
                        "Fatal error parsing GDB trace",
                        line_no=line_no,
                    )

                # This is a workaround for GDB throwing an error while resolving
                # function arguments in the trace and aborting. We try to remove the
                # error message to at least recover the function name properly.
                gdbErrorIdx = functionName.find(" (/build/buildd/gdb")
                if gdbErrorIdx > 0:
                    functionName = functionName[:gdbErrorIdx]

                if gdbDebugInfoMismatch:
                    # Remove addtional signature segment
                    functionName = ReportInfo.sanitizeStackFrame(functionName)

                self.backtrace.append(functionName)

        if self.reportInstruction is not None:
            # Remove any leading/trailing whitespaces
            self.reportInstruction = self.reportInstruction.strip()

        # If we have no report address but the instruction, try to calculate the report
        # address
        if self.reportAddress is None and self.reportInstruction is not None:
            reportAddress = GDBReportInfo.calculateReportAddress(
                self.reportInstruction, self.registers
            )

            if isinstance(reportAddress, (str, bytes)):
                self.failureReason = reportAddress
                return

            self.reportAddress = reportAddress

            if self.reportAddress is not None and self.reportAddress < 0:
                if RegisterHelper.getBitWidth(self.registers) == 32:
                    self.reportAddress = uint32(self.reportAddress)
                else:
                    # Assume 64 bit width
                    self.reportAddress = uint64(self.reportAddress)

    @staticmethod
    def calculateReportAddress(reportInstruction, registerMap):
        """
        Calculate the report address given the report instruction and register contents

        @type reportInstruction: string
        @param reportInstruction: Report instruction string as provided by GDB
        @type registerMap: Map from string to int
        @param registerMap: Map of register names to values

        @rtype: int
        @return The calculated report address

        On error, a string containing the failure message is returned instead.
        """

        if not reportInstruction:
            # GDB shows us no instruction, so the memory at the instruction
            # pointer address must be inaccessible and we should assume
            # that this caused our report.
            return RegisterHelper.getInstructionPointer(registerMap)

        parts = reportInstruction.split(None, 1)

        if len(parts) == 1:
            # Single instruction without any operands?
            # Only accept those that we explicitly know so far.

            instruction = parts[0]

            if instruction == "ret" or instruction == "retq":
                # If ret is reporting, it's most likely due to the stack pointer
                # pointing somewhere where it shouldn't point, so use that as
                # the report address.
                return RegisterHelper.getStackPointer(registerMap)
            elif instruction == "ud2" or instruction == "(bad)":
                # ud2 - Raise invalid opcode exception
                # We treat this like invalid instruction
                #
                # (bad) - Assembly at the instruction pointer is not valid
                # We also consider this an invalid instruction
                return RegisterHelper.getInstructionPointer(registerMap)
            else:
                raise RuntimeError(
                    f"Unsupported non-operand instruction: {instruction}"
                )

        if len(parts) != 2:
            raise RuntimeError(
                f"Failed to split instruction and operands apart: {reportInstruction}"
            )

        instruction = parts[0]
        operands = parts[1]

        if not re.match("[a-z\\.]+", instruction):
            raise RuntimeError(f"Invalid instruction: {instruction}")

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
                    return (None, f"Missing value for register {match.group(2)} ")
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
                    # push/pop/call are quite special because they can perform an
                    # optional memory dereference before touching the stack. We don't
                    # know for sure which of the two operations fail if we detect a
                    # deref in the instruction, but for now we assume that the deref
                    # fails and the stack pointer is ok.
                    #
                    # TODO: Fix this properly by including readability information in
                    #       GDB output
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
                            #    (gdb) p $_siginfo._sifields._sigfault.si_addr
                            #      $1 = (void *) 0x7ff846e64d28
                            #      (gdb) x /i $pc
                            # noqa => 0x876b40 <js::ArgumentsObject::create<CopyFrameArgs>(JSContext*, JS::HandleScript, JS::HandleFunction, unsigned int, CopyFrameArgs&)+528>:   movsq  %ds:(%rsi),%es:(%rdi)
                            #      (gdb) info reg $ds
                            #      ds             0x0      0
                            #      (gdb) info reg $es
                            #      es             0x0      0
                            #      (gdb) info reg $rsi
                            #      rsi            0x7ff846e64d28   140704318115112
                            #      (gdb) info reg $rdi
                            #      rdi            0x7fff27fac030   140733864132656
                            #
                            #
                            # We don't support this right now, so return None.
                            #
                            return None

                        raise RuntimeError(
                            "Instruction operands have multiple loads? "
                            f"{reportInstruction}"
                        )

                    derefOp = parts[1]

                if derefOp is not None:
                    (val, failed) = calculateDerefOpAddress(derefOp)
                    if failed:
                        failureReason = failed
                    else:
                        return val
                else:
                    failureReason = (
                        "Failed to decode two-operand instruction: No dereference "
                        "operation or hardcoded address detected."
                    )
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

                    (result, reason) = GDBReportInfo.calculateComplexDerefOpAddress(
                        complexDerefOp, registerMap
                    )

                    if result is None:
                        failureReason = reason
                    else:
                        return result
                else:
                    raise RuntimeError(
                        f"Unexpected instruction pattern: {reportInstruction}"
                    )
            elif len(parts) == 4:
                if "(" in parts[0] and ")" not in parts[0]:
                    complexDerefOp = parts[0] + "," + parts[1] + "," + parts[2]
                elif "(" not in parts[0] and ")" not in parts[0]:
                    complexDerefOp = parts[1] + "," + parts[2] + "," + parts[3]

                (result, reason) = GDBReportInfo.calculateComplexDerefOpAddress(
                    complexDerefOp, registerMap
                )

                if result is None:
                    failureReason = reason
                else:
                    return result
            else:
                raise RuntimeError(
                    "Unexpected length after splitting operands of this instruction: %s"
                    % reportInstruction
                )

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
                    return (None, f"Missing value for register {derefOps[0]} ")
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
                    # This is an instruction that the dissassembler can't read, so
                    # likely a SIGILL
                    return RegisterHelper.getInstructionPointer(registerMap)
            elif len(parts) == 2:
                if instruction.startswith("ldr") or instruction.startswith("str"):
                    # Load/Store instruction
                    match = re.match("^\\s*\\[(.*)\\]$", parts[1])
                    if match is not None:
                        (result, reason) = calculateARMDerefOpAddress(match.group(1))
                        if result is None:
                            failureReason += f" ({reason})"
                        else:
                            return result
        else:
            failureReason = "Architecture is not supported."

        print(
            "Unable to calculate report address from instruction: "
            f">{reportInstruction}<",
            file=sys.stderr,
        )
        print(f"Reason: {failureReason}", file=sys.stderr)
        return failureReason

    @staticmethod
    def calculateComplexDerefOpAddress(complexDerefOp, registerMap):
        match = re.match(
            "((?:\\-?0x[0-9a-f]+)?)\\(%([a-z0-9]+),%([a-z0-9]+),([0-9]+)\\)",
            complexDerefOp,
        )
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
                    return (None, f"Missing value for register {match.group(2)}")
                else:
                    return (None, f"Missing value for register {match.group(3)}")

            if RegisterHelper.getBitWidth(registerMap) == 32:
                val = int32(uint32(regA) + uint32(offset) + uint32(regB) * uint32(mult))
            else:
                # Assume 64 bit width
                val = int64(uint64(regA) + uint64(offset) + uint64(regB) * uint64(mult))
            return (int(val), None)

        return (None, "Unknown failure.")


class MinidumpReportInfo(ReportInfo):
    def __init__(self, stdout, stderr, configuration, reportData=None):
        """
        Private constructor, called by L{ReportInfo.fromRawReportData}. Do not use
        directly.
        """
        ReportInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if reportData is not None:
            self.rawReportData.extend(reportData)

        self.configuration = configuration

        # If reportData is given, use that to find the Minidump trace, otherwise use
        # stderr
        if reportData:
            minidumpOuput = reportData
        else:
            minidumpOuput = stderr

        reportThread = None
        for traceLine in minidumpOuput:
            if reportThread is not None:
                if traceLine.startswith(f"{reportThread}|"):
                    components = traceLine.split("|")

                    if not components[3]:
                        # If we have no symbols, but we have a library/component, using
                        # that allows us to match on the libary name in the stack which
                        # is helpful for reports in low level libraries.
                        if components[2]:
                            frame = components[2]
                            if len(components) >= 7 and components[6]:
                                frame = f"{frame}+{components[6]}"
                            self.backtrace.append(ReportInfo.sanitizeStackFrame(frame))
                        else:
                            self.backtrace.append("??")
                    else:
                        self.backtrace.append(
                            ReportInfo.sanitizeStackFrame(components[3])
                        )
            elif traceLine.startswith("Report|"):
                components = traceLine.split("|")
                reportThread = int(components[3])
                self.reportAddress = int(components[2], 16)


class AppleReportInfo(ReportInfo):
    def __init__(self, stdout, stderr, configuration, reportData=None):
        """
        Private constructor, called by L{ReportInfo.fromRawReportData}. Do not use
        directly.
        """
        ReportInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if reportData is not None:
            self.rawReportData.extend(reportData)

        self.configuration = configuration

        apple_report_data = reportData or stderr

        inReportingThread = False
        for line in apple_report_data:
            # Report address
            if line.startswith("Exception Codes:"):
                # Example:
                #     Exception Type:        EXC_BAD_ACCESS (SIGABRT)
                #     Exception Codes:       KERN_INVALID_ADDRESS at 0x00000001374b893e
                address = line.split(" ")[-1]
                if address.startswith("0x"):
                    self.reportAddress = int(address, 16)

            # Start of stack for reporting thread
            if re.match(r"Thread \d+ Reported:", line):
                inReportingThread = True
                continue

            if line.strip() == "":
                inReportingThread = False
                continue

            if inReportingThread:
                # Example:
                # noqa "0   js-dbg-64-dm-darwin-a523d4c7efe2    0x00000001004b04c4 js::jit::MacroAssembler::Pop(js::jit::Register) + 180 (MacroAssembler-inl.h:50)"
                components = line.split(None, 3)
                stackEntry = components[3]
                if stackEntry.startswith("0"):
                    self.backtrace.append("??")
                else:
                    stackEntry = AppleReportInfo.removeFilename(stackEntry)
                    stackEntry = AppleReportInfo.removeOffset(stackEntry)
                    stackEntry = ReportInfo.sanitizeStackFrame(stackEntry)
                    self.backtrace.append(stackEntry)

    @staticmethod
    def removeFilename(stackEntry):
        match = re.match(r"(.*) \(\S+\)", stackEntry)
        if match:
            return match.group(1)
        return stackEntry

    @staticmethod
    def removeOffset(stackEntry):
        match = re.match(r"(.*) \+ \d+", stackEntry)
        if match:
            return match.group(1)
        return stackEntry


class CDBReportInfo(ReportInfo):
    def __init__(self, stdout, stderr, configuration, reportData=None):
        """
        Private constructor, called by L{ReportInfo.fromRawReportData}. Do not use
        directly.
        """
        ReportInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if reportData is not None:
            self.rawReportData.extend(reportData)

        self.configuration = configuration

        cdbRegisterPattern = RegisterHelper.getRegisterPattern() + "=([0-9a-f]+)"

        address = ""
        inReportingThread = False
        inReportInstruction = False
        inEcxrData = False
        ecxrData = []
        cInstruction = ""

        cdb_report_data = reportData or stderr

        for line in cdb_report_data:
            # Start of .ecxr data
            if re.match(r"0:000> \.ecxr", line):
                inEcxrData = True
                continue

            if inEcxrData:
                # 32-bit example:
                #      0:000> .ecxr
                # noqa eax=02efff01 ebx=016fddb8 ecx=2b2b2b2b edx=016fe490 esi=02e00310 edi=02e00310
                # noqa eip=00404c59 esp=016fdc2c ebp=016fddb8 iopl=0         nv up ei pl nz na po nc
                # noqa cs=0023  ss=002b  ds=002b  es=002b  fs=0053  gs=002b             efl=00010202
                # 64-bit example:
                #      0:000> .ecxr
                #      rax=00007ff74d8fee30 rbx=00000285ef400420 rcx=2b2b2b2b2b2b2b2b
                #      rdx=00000285ef21b940 rsi=000000e87fbfc340 rdi=00000285ef400420
                #      rip=00007ff74d469ff3 rsp=000000e87fbfc040 rbp=fffe000000000000
                #       r8=000000e87fbfc140  r9=000000000001fffc r10=0000000000000649
                #      r11=00000285ef25a000 r12=00007ff74d9239a0 r13=fffa7fffffffffff
                #      r14=000000e87fbfd0e0 r15=0000000000000003
                #      iopl=0         nv up ei pl nz na pe nc
                # noqa cs=0033  ss=002b  ds=002b  es=002b  fs=0053  gs=002b             efl=00010200
                if line.startswith("cs="):
                    inEcxrData = False
                    continue

                # Report address
                # Extract the eip/rip specifically for use later
                if "eip=" in line:
                    address = line.split("eip=")[1].split()[0]
                    self.reportAddress = int(address, 16)
                elif "rip=" in line:
                    address = line.split("rip=")[1].split()[0]
                    self.reportAddress = int(address, 16)

                # First extract the line
                # 32-bit example:
                #     eax=02efff01 ebx=016fddb8 ecx=2b2b2b2b esi=02e00310 edi=02e00310
                # 64-bit example:
                #     rax=00007ff74d8fee30 rbx=00000285ef400420 rcx=2b2b2b2b2b2b2b2b
                matchLine = re.search(RegisterHelper.getRegisterPattern(), line)
                if matchLine is not None:
                    ecxrData.extend(line.split())

                # Next, put the eax/rax, ebx/rbx, etc. entries into a list of their own,
                # then iterate
                match = re.search(cdbRegisterPattern, line)
                for instr in ecxrData:
                    match = re.search(cdbRegisterPattern, instr)
                    if match is not None:
                        register = match.group(1)
                        value = int(match.group(2), 16)
                        self.registers[register] = value

            # Report instruction
            # Start of report instruction details
            if line.startswith("FAULTING_IP"):
                inReportInstruction = True
                continue

            if inReportInstruction and not cInstruction:
                if "PROCESS_NAME" in line:
                    inReportInstruction = False
                    continue

                # 64-bit binaries have a backtick in their addresses,
                # e.g. 00007ff7`1e424e62
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
                    self.reportInstruction = cInstruction

            # Start of stack for reporting thread
            if line.startswith("STACK_TEXT:"):
                inReportingThread = True
                continue

            if inReportingThread:
                # 32-bit example:
                # noqa  "016fdc38 004b2387 01e104e8 016fe490 016fe490 js_32_dm_windows_62f79d676e0e!JSObject::allocKindForTenure+0x9"
                # 64-bit example:
                # noqa  "000000e8`7fbfc040 00007ff7`4d53a984 : 000000e8`7fbfc2c0 00000285`ef7bb400 00000285`ef21b000 00007ff7`4d4254b9 : js_64_dm_windows_62f79d676e0e!JSObject::allocKindForTenure+0x13"
                if (
                    "STACK_COMMAND" in line
                    or "SYMBOL_NAME" in line
                    or "THREAD_SHA1_HASH_MOD_FUNC" in line
                    or "FAULTING_SOURCE_CODE" in line
                ):
                    inReportingThread = False
                    continue

                # Ignore cdb error and empty lines
                if "Following frames may be wrong." in line or line.strip() == "":
                    continue

                stackEntry = CDBReportInfo.removeFilenameAndOffset(line)
                stackEntry = ReportInfo.sanitizeStackFrame(stackEntry)
                self.backtrace.append(stackEntry)

    @staticmethod
    def removeFilenameAndOffset(stackEntry):
        # Extract only the function name
        if "0x" in stackEntry:
            result = (
                stackEntry.split("!")[-1].split("+")[0].split("<")[0].split(" ")[-1]
            )
            if "0x" in result:
                result = "??"  # Sometimes there is only a memory address in the stack
            elif ".exe" in result:
                # Sometimes the binary name is present:
                # eg. "00000000 00000000 unknown!js-dbg-32-windows-42c95d88aaaa.exe+0x0"
                result = "??"
        else:
            result = "??"
        return result


class RustReportInfo(ReportInfo):
    RE_FRAME = re.compile(
        r"^( +\d+:( +0x[0-9a-f]+ -)? (?P<symbol>.+?)"
        r"(::h[0-9a-f]{16})?|\s+at ([A-Za-z]:)?(/[A-Za-z0-9_ .]+)+:\d+)$"
    )

    def __init__(self, stdout, stderr, configuration, reportData=None):
        """
        Private constructor, called by L{ReportInfo.fromRawReportData}. Do not use
        directly.
        """
        ReportInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if reportData is not None:
            self.rawReportData.extend(reportData)

        self.configuration = configuration

        # If reportData is given, use that to find the rust backtrace, otherwise use
        # stderr
        rustOutput = reportData or stderr

        self.reportAddress = (
            0  # this is always an assertion, set to 0 to make matching more efficient
        )

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


class TSanReportInfo(ReportInfo):
    def __init__(self, stdout, stderr, configuration, reportData=None):
        """
        Private constructor, called by L{ReportInfo.fromRawReportData}. Do not use
        directly.
        """
        ReportInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if reportData is not None:
            self.rawReportData.extend(reportData)

        self.configuration = configuration

        # If reportData is given, use that to find the ASan trace, otherwise use stderr
        tsanOutput = reportData if reportData else stderr

        tsanWarningPattern = r"""WARNING: ThreadSanitizer:.*\s.+?\s+\(pid=\d+\)"""

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

            index, parts = ASanReportInfo.split_frame(traceLine)
            if index is None:
                continue

            # We may see multiple traces in TSAN
            if index == 0:
                if currentBacktrace is not None:
                    backtraces.append(currentBacktrace)
                currentBacktrace = []
                expectedIndex = 0

            if not expectedIndex == index:
                print(
                    f"Error parsing TSan trace (Index mismatch, got index {index} but "
                    f"expected {expectedIndex})",
                    file=sys.stderr,
                )
                break

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
                print(
                    f"Warning: Missing component in this line: {traceLine}",
                    file=sys.stderr,
                )
                component = "<missing>"

            currentBacktrace.append(ReportInfo.sanitizeStackFrame(component))

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

    @unicode_escape_result
    def createShortSignature(self):
        """
        @rtype: String
        @return: A string representing this report (short signature)
        """
        if self.tsanWarnLine:
            msg = re.sub(r"\s*\(pid=\d+\)", "", self.tsanWarnLine)
            msg = msg.replace("WARNING: ", "")

            if "data race" in msg or "race on external object" in msg:
                if self.tsanIndexZero:
                    msg += f" [@ {self.tsanIndexZero[0]}]"
                    if len(self.tsanIndexZero) > 1:
                        msg += f" vs. [@ {self.tsanIndexZero[1]}]"
            elif "thread leak" in msg:
                if self.tsanIndexZero:
                    msg += f" [@ {self.tsanIndexZero[0]}]"
            elif "mutex" in msg or "deadlock" in msg:
                for frame in self.backtrace:
                    # This is a heuristic for finding an interesting frame
                    # that does not refer to a mutex primitive.
                    if "mutex" not in frame:
                        msg += f" [@ {frame}]"
                        break
            elif "signal" in msg or "use-after-free" in msg:
                if self.backtrace:
                    msg += f" [@ {self.backtrace[0]}]"
            else:
                raise RuntimeError(
                    "Fatal error: TSan trace warning line has unhandled message case: "
                    f"{msg}"
                )

            return msg

        return "No TSan warning detected"


class ValgrindReportInfo(ReportInfo):
    MSG_REGEX = re.compile(
        r"""
        ==\d+==\s+(?P<msg>
        (\d+(,\d+)*\sbytes\sin\s\d+(,\d+)*\sblocks\sare\s\w+\slost)|
        (Argument\s'\w+'\sof\sfunction\smalloc.+)|
        ((Conditional|Use)\s.+?uninitialised\svalue.+)|
        (Invalid\s\w+\sof\ssize.+)|
        ((Invalid|Mismatched)\sfree\(\).+)|
        (Process\sterminating\swith\sdefault\saction.+)|
        (Source\sand\sdestination\soverlap)|
        (Syscall\sparam.+)
        )""",
        re.VERBOSE,
    )

    def __init__(self, stdout, stderr, configuration, reportData=None):
        """
        Private constructor, called by L{ReportInfo.fromRawReportData}. Do not use
        directly.
        """
        ReportInfo.__init__(self)

        if stdout is not None:
            self.rawStdout.extend(stdout)

        if stderr is not None:
            self.rawStderr.extend(stderr)

        if reportData is not None:
            self.rawReportData.extend(reportData)

        self.configuration = configuration

        # If reportData is given, use that to find the Valgrind trace, otherwise use
        # stderr
        vgdOutput = reportData if reportData else stderr
        stackPattern = re.compile(
            r"""
            ^==\d+==\s+(at|by)\s+            # beginning of entry
            0x[0-9A-Fa-f]+\:\s+              # address
            (?P<func>.+)\s+                  # function name
            \((in\s+)?(?P<file>.+?)(:.+?)?\) # file name
            """,
            re.VERBOSE,
        )

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
                self.backtrace.append(ReportInfo.sanitizeStackFrame(lineFunc))

            elif self.backtrace:
                # check if address info is available
                addr = re.match(
                    r"^==\d+==\s+Address\s(?P<addr>0x[0-9A-Fa-f]+)\s", traceLine
                )
                if addr:
                    self.reportAddress = int(addr.group("addr"), 16)
                # look for '==PID== \n' to indicate the end of a trace
                if re.match(r"^==\d+==\s+$", traceLine) is not None:
                    # done parsing
                    break

    @unicode_escape_result
    def createShortSignature(self):
        """
        @rtype: String
        @return: A string representing this report (short signature)
        """

        logData = self.rawReportData if self.rawReportData else self.rawStderr
        for line in logData:
            m = re.match(ValgrindReportInfo.MSG_REGEX, line)
            if m and m.group("msg"):
                if self.backtrace:
                    return f"Valgrind: {m.group('msg')} [@ {self.backtrace[0]}]"
                return f"Valgrind: {m.group('msg')}"

        if not self.backtrace:
            return "No report detected"
        return f"Valgrind: [@ {self.backtrace[0]}]"
