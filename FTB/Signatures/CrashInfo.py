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
import re
import sys
from FTB.Signatures import RegisterHelper
from FTB.Signatures.CrashSignature import CrashSignature
from FTB.ProgramConfiguration import ProgramConfiguration

from numpy import int32, int64, uint32, uint64
import json
from FTB import AssertionHelper
import os

class CrashInfo():
    '''
    Abstract base class that provides a method to instantiate the right sub class.
    It also supports generating a CrashSignature based on the stored information.
    '''
    __metaclass__ = ABCMeta
    
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
            buf.append("# %02d    %s" %(idx, frame))
        buf.append("")
        
        if self.crashAddress:
            buf.append("Crash address: %s" % self.crashAddress)
            
        if self.crashInstruction:
            buf.append("Crash instruction: %s" % self.crashInstruction)
        
        if self.crashAddress or self.crashInstruction:
            buf.append("")
        
        buf.append("Last 5 lines on stderr:")
        buf.extend(self.rawStderr[-5:])
        
        return "\n".join(buf)
    
    @staticmethod
    def fromRawCrashData(stdout, stderr, configuration, auxCrashData=None):
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
        
        @rtype: CrashInfo
        @return: Crash information object
        '''
        
        assert stdout == None or isinstance(stdout, list) or isinstance(stdout, basestring)
        assert stderr == None or isinstance(stderr, list) or isinstance(stderr, basestring)
        assert auxCrashData ==None or isinstance(auxCrashData, list) or isinstance(auxCrashData, basestring)
        
        assert isinstance(configuration, ProgramConfiguration)
        
        if isinstance(stdout, basestring):
            stdout = stdout.splitlines()
        
        if isinstance(stderr, basestring):
            stderr = stderr.splitlines()
        
        if isinstance(auxCrashData, basestring):
            auxCrashData = auxCrashData.splitlines()
        
        asanString = "ERROR: AddressSanitizer:"
        gdbString = "Program received signal "
        gdbCoreString = "Program terminated with signal "
        
        # Search both crashData and stderr, but prefer crashData
        lines = []
        if (auxCrashData != None):
            lines.extend(auxCrashData)
        if (stderr != None):
            lines.extend(stderr)
        
        for line in lines:
            if asanString in line:
                return ASanCrashInfo(stdout, stderr, configuration, auxCrashData)
            elif gdbString in line or gdbCoreString in line:
                return GDBCrashInfo(stdout, stderr, configuration, auxCrashData)
        
        # Default fallback to be used if there is neither ASan nor GDB output.
        # This is still useful in case there is no crash but we want to match
        # e.g. stdout/stderr output with signatures.
        return NoCrashInfo(stdout, stderr, configuration, auxCrashData)
    
    def createShortSignature(self):
        '''
        @rtype: String
        @return: A string representing this crash (short signature)
        '''
        # See if we have an abort message and if so, use that as short signature
        abortMsg = AssertionHelper.getAssertion(self.rawStderr, True)
        if abortMsg != None:
            return abortMsg
        
        if not len(self.backtrace):
            return "No crash detected"
        
        return "[@ %s]" % self.backtrace[0]
    
    def createCrashSignature(self, forceCrashAddress=False, forceCrashInstruction=False, maxFrames=8, minimumSupportedVersion=12):
        '''
        @param forceCrashAddress: If True, the crash address will be included in any case
        @type forceCrashAddress: bool
        @param forceCrashInstruction: If True, the crash instruction will be included in any case
        @type forceCrashInstruction: bool
        @param maxFrames: How many frames (at most) should be included in the signature
        @type maxFrames: int
        
        @param minimumSupportedVersion: The minimum crash signature standard version that the 
                                        generated signature should be valid for (10 => 1.0, 12 => 1.2)
        @type minimumSupportedVersion: int
        
        @rtype: CrashSignature
        @return: A crash signature object
        '''
        # Determine the actual number of frames based on how many we got
        if len(self.backtrace) > maxFrames:
            numFrames = maxFrames
        else:
            numFrames = len(self.backtrace)
        
        # See if we have an abort message and if so, get a sanitized version of it
        abortMsg = AssertionHelper.getAssertion(self.rawStderr, True)
        if abortMsg != None:
            abortMsg = AssertionHelper.getSanitizedAssertionPattern(abortMsg)
        
        # Consider the first four frames as top stack
        topStackLimit = 4
        
        symptomArr = []
        
        if abortMsg != None:
            # Compose StringMatch object with PCRE pattern.
            # Versions below 1.2 only support the full object PCRE style,
            # for anything newer, use the short form with forward slashes
            # to increase the readability of the signatures. 
            if minimumSupportedVersion < 12:
                stringObj = { "value" : abortMsg, "matchType" : "pcre" }
                symptomObj = { "type" : "output", "src" : "stderr", "value" : stringObj }            
            else:
                symptomObj = { "type" : "output", "src" : "stderr", "value" : "/%s/" % abortMsg }
            symptomArr.append(symptomObj)
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
                    symptomObj = { "type" : "stackFrame", "frameNumber" : idx, "functionName" : functionName }
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
            for frameIdx in range(0,len(framesArray)):
                if str(framesArray[frameIdx]) != '?':
                    lastSymbolizedFrame = frameIdx
            
            if lastSymbolizedFrame != None:
                # Remove all elements behind the last symbolized frame
                framesArray = framesArray[:lastSymbolizedFrame + 1]
            else:
                # We don't have a single symbolized frame, so it doesn't make sense
                # to keep any wildcards in case we added some for unsymbolized frames.
                framesArray = []
                
            if framesArray:
                symptomArr.append({ "type" : "stackFrames", "functionNames" : framesArray })

        # Missing too much of the top stack frames, add additional crash information
        stackIsInsufficient = topStackMissCount >= 2 and abortMsg == None 
        
        includeCrashAddress = stackIsInsufficient or forceCrashAddress
        includeCrashInstruction = (stackIsInsufficient and self.crashInstruction != None) or forceCrashInstruction
        
        if includeCrashAddress:
            if self.crashAddress == None:
                if self.failureReason == None:
                    self.failureReason = "No crash address available from crash data."
                return None

            crashAddress = hex(self.crashAddress).rstrip("L")
            
            crashAddressSymptomObj = { "type" : "crashAddress", "address" : crashAddress }
            symptomArr.append(crashAddressSymptomObj)
        
        if includeCrashInstruction:
            if self.crashInstruction == None:
                if self.failureReason == None:
                    self.failureReason = "No crash instruction available from crash data."
                return None
            
            crashInstructionSymptomObj = { "type" : "instruction", "instructionName" : self.crashInstruction }
            symptomArr.append(crashInstructionSymptomObj)
        
        sigObj = { "symptoms" : symptomArr }
        
        return CrashSignature(json.dumps(sigObj, indent=2))

class NoCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)
        
        if stdout != None:
            self.rawStdout.extend(stdout)
            
        if stderr != None:
            self.rawStderr.extend(stderr)
        
        if crashData != None:
            self.rawCrashData.extend(crashData)
        
        self.configuration = configuration
    
class ASanCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)
        
        if stdout != None:
            self.rawStdout.extend(stdout)
            
        if stderr != None:
            self.rawStderr.extend(stderr)
        
        if crashData != None:
            self.rawCrashData.extend(crashData)
        
        self.configuration = configuration
        
        # If crashData is given, use that to find the ASan trace, otherwise use stderr
        if crashData == None:
            asanOutput = stderr
        else:
            asanOutput = crashData

        # For better readability, list all the formats here, then join them into the regular expression
        asanMessages = [
            "on address", # The most common format, used for all overflows
            "on unknown address", # Used in case of a SIGSEGV
            "double-free on", # Used in case of a double-free
            "not malloc\\(\\)\\-ed:", # Used in case of a wild free (on unallocated memory)
            "not owned:" # Used when calling __asan_get_allocated_size() on a pointer that isn't owned
        ]
        
        # TODO: Support "memory ranges [%p,%p) and [%p, %p) overlap" ?
        
        asanCrashAddressPattern = " AddressSanitizer:.+ (?:" + "|".join(asanMessages) + ")\\s+0x([0-9a-f]+)"
        asanRegisterPattern = "(?:\\s+|\\()pc\\s+0x([0-9a-f]+)\\s+(sp|bp)\\s+0x([0-9a-f]+)\\s+(sp|bp)\\s+0x([0-9a-f]+)"
        
        expectedIndex = 0
        for traceLine in asanOutput:
            if self.crashAddress == None:
                match = re.search(asanCrashAddressPattern, traceLine)
                
                if match != None:
                    self.crashAddress = long(match.group(1), 16)
                
                    # Crash Address and Registers are in the same line for ASan
                    match = re.search(asanRegisterPattern, traceLine)
                    if match != None:
                        self.registers["pc"] = long(match.group(1), 16)
                        self.registers[match.group(2)] = long(match.group(3), 16)
                        self.registers[match.group(4)] = long(match.group(5), 16)
                    else:
                        raise RuntimeError("Fatal error parsing ASan trace: Failed to isolate registers in line: %s" % traceLine)

                    
            parts = traceLine.strip().split()
                        
            # We only want stack frames
            if not parts or not parts[0].startswith("#"):
                continue
            
            index = int(parts[0][1:])
            
            # We may see multiple traces in ASAN
            if index == 0:
                expectedIndex = 0
            
            if not expectedIndex == index:
                raise RuntimeError("Fatal error parsing ASan trace (Index mismatch, got index %s but expected %s)" % (index, expectedIndex) )
            
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
                
            self.backtrace.append(component)
            expectedIndex += 1
        
class GDBCrashInfo(CrashInfo):
    def __init__(self, stdout, stderr, configuration, crashData=None):
        '''
        Private constructor, called by L{CrashInfo.fromRawCrashData}. Do not use directly.
        '''
        CrashInfo.__init__(self)
        
        if stdout != None:
            self.rawStdout.extend(stdout)
            
        if stderr != None:
            self.rawStderr.extend(stderr)
        
        if crashData != None:
            self.rawCrashData.extend(crashData)
            
        self.configuration = configuration
        
        # If crashData is given, use that to find the GDB trace, otherwise use stderr
        if crashData == None:
            gdbOutput = stderr
        else:
            gdbOutput = crashData
        
        gdbFramePatterns = [
                            "\\s*#(\\d+)\\s+(0x[0-9a-f]+) in (.+?) \\(.*?\\)( at .+)?",
                            "\\s*#(\\d+)\\s+()(.+?) \\(.*?\\)( at .+)?"
                            ]
        
        gdbRegisterPattern = RegisterHelper.getRegisterPattern() + "\\s+0x([0-9a-f]+)"
        gdbCrashAddressPattern = "Crash Address:\\s+0x([0-9a-f]+)"
        gdbCrashInstructionPattern = "=> 0x[0-9a-f]+(?: <.+>)?:\\s+(.+)"
        
        lastLineBuf = ""
        
        pastFrames = False
        
        for traceLine in gdbOutput:
            # Do a very simple check for a frame number in combination with pending
            # buffer content. If we detect this constellation, then it's highly likely
            # that we have a valid trace line but no pattern that fits it. We need
            # to make sure that we report this.
            if not pastFrames and re.match("\\s*#\\d+.+", lastLineBuf) != None and re.match("\\s*#\\d+.+", traceLine) != None:
                print("Fatal error parsing this GDB trace line:", file=sys.stderr)
                print(lastLineBuf, file=sys.stderr)
                raise RuntimeError("Fatal error parsing GDB trace")
            
            if not len(lastLineBuf):
                match = re.search(gdbRegisterPattern, traceLine)
                if match != None:
                    pastFrames = True;
                    register = match.group(1)
                    value = long(match.group(2), 16)
                    self.registers[register] = value
                else:
                    match = re.search(gdbCrashAddressPattern, traceLine)
                    if match != None:
                        self.crashAddress = long(match.group(1), 16)
                    else:
                        match = re.search(gdbCrashInstructionPattern, traceLine)
                        if match != None:
                            self.crashInstruction = match.group(1)
            
            if not pastFrames:
                if not len(lastLineBuf) and re.match("\\s*#\\d+.+", traceLine) == None:
                    # Skip additional lines
                    continue
                
                lastLineBuf += traceLine
                
                functionName = None
                frameIndex = None
                
                for gdbPattern in gdbFramePatterns:
                    match = re.search(gdbPattern, lastLineBuf)
                    if match != None:
                        frameIndex = int(match.group(1))
                        functionName = match.group(3)
                        break
                
                if frameIndex == None:
                    # Line might not be complete yet, try adding the next
                    continue
                else:
                    # Successfully parsed line, reset last line buffer
                    lastLineBuf = ""
                
                # Allow #0 to appear twice in the beginning, GDB does this for core dumps ... 
                if len(self.backtrace) != frameIndex and frameIndex == 0:
                    self.backtrace.pop(0)
                elif len(self.backtrace) != frameIndex:
                    print("Fatal error parsing this GDB trace (Index mismatch, wanted %s got %s ): " % (len(self.backtrace), frameIndex), file=sys.stderr)
                    print(os.linesep.join(gdbOutput) , file=sys.stderr)
                    raise RuntimeError("Fatal error parsing GDB trace")

                # This is a workaround for GDB throwing an error while resolving function arguments
                # in the trace and aborting. We try to remove the error message to at least recover
                # the function name properly.
                gdbErrorIdx = functionName.find(" (/build/buildd/gdb")
                if gdbErrorIdx > 0:
                    functionName = functionName[:gdbErrorIdx]
                
                self.backtrace.append(functionName)
        
        # If we have no crash address but the instruction, try to calculate the crash address
        if self.crashAddress == None and self.crashInstruction != None:
            crashAddress = GDBCrashInfo.calculateCrashAddress(self.crashInstruction, self.registers)
            
            if isinstance(crashAddress, basestring):
                self.failureReason = crashAddress
                return
            
            self.crashAddress = crashAddress
            
            if (self.crashAddress != None and self.crashAddress < 0):
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
        @type registerMap: Map from string to long
        @param registerMap: Map of register names to values
        
        @rtype: long
        @return The calculated crash address
        
        On error, a string containing the failure message is returned instead.
        '''
        parts = crashInstruction.split(None, 1)
        
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
        
        if RegisterHelper.isX86Compatible(registerMap):
            if len(parts) == 1:
                if instruction == "callq" or instruction == "push":
                    return RegisterHelper.getStackPointer(registerMap)
                else:
                    failureReason = "Unsupported single-operand instruction."
            elif len(parts) == 2:
                failureReason = "Unknown failure with two-operand instruction."
                derefOp = None
                if "(" in parts[0] and ")" in parts[0]:
                    derefOp = parts[0]
                
                if "(" in parts[1] and ")" in parts[1]:
                    if derefOp != None:
                        if ":(" in parts[1]:
                            # This can be an instruction using multiple segments, like:
                            #     
                            #   movsq  %ds:(%rsi),%es:(%rdi)
                            #   
                            #  (gdb) p $_siginfo._sifields._sigfault.si_addr
                            #    $1 = (void *) 0x7ff846e64d28
                            #    (gdb) x /i $pc
                            #    => 0x876b40 <js::ArgumentsObject::create<CopyFrameArgs>(JSContext*, JS::HandleScript, JS::HandleFunction, unsigned int, CopyFrameArgs&)+528>:   movsq  %ds:(%rsi),%es:(%rdi)
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

                if derefOp != None:
                    match = re.match("((?:\\-?0x[0-9a-f]+)?)\\(%([a-z0-9]+)\\)", derefOp)
                    if match != None:
                        offset = 0L
                        if len(match.group(1)):
                            offset = long(match.group(1), 16)

                        val = RegisterHelper.getRegisterValue(match.group(2), registerMap)
                        
                        # If we don't have the value, return None
                        if val == None:
                            failureReason = "Missing value for register %s " % match.group(2)
                        else:
                            if RegisterHelper.getBitWidth(registerMap) == 32:
                                return long(int32(uint32(offset)) + int32(uint32(val)))
                            else:
                                # Assume 64 bit width
                                return long(int64(uint64(offset)) + int64(uint64(val)))
                else:
                    failureReason = "Failed to decode two-operand instruction: No dereference operation or hardcoded address detected."
                    # We might still be reading from/writing to a hardcoded address.
                    # Note that it's not possible to have two hardcoded addresses
                    # in one instruction, one operand must be a register or immediate
                    # constant (denoted by leading $). In some cases, like a movabs
                    # instruction, the immediate constant however is dereferenced
                    # and is the first operator. So we first check parts[1] then
                    # parts[0] in case it's a dereferencing operation.
                    
                    for x in (parts[1],parts[0]):
                        result = re.match("\\$?(\\-?0x[0-9a-f]+)", x)
                        if  result != None:
                            return long(result.group(1), 16)
            elif len(parts) == 3:
                # Example instruction: shrb   -0x69(%rdx,%rbx,8)
                if "(" in parts[0] and ")" in parts[2]:
                    complexDerefOp = parts[0] + "," + parts[1] + "," + parts[2]
                    
                    (result, reason) = GDBCrashInfo.calculateComplexDerefOpAddress(complexDerefOp, registerMap)
                    
                    if result == None:
                        failureReason = reason
                    else:
                        return result
                else:
                    raise RuntimeError("Unexpected instruction pattern: %s" % crashInstruction)
            elif len(parts) == 4:
                if "(" in parts[0] and not ")" in parts[0]:
                    complexDerefOp = parts[0] + "," + parts[1] + "," + parts[2]
                elif not "(" in parts[0] and not ")" in parts[0]:
                    complexDerefOp = parts[1] + "," + parts[2] + "," + parts[3]
                
                (result, reason) = GDBCrashInfo.calculateComplexDerefOpAddress(complexDerefOp, registerMap)
                    
                if result == None:
                    failureReason = reason
                else:
                    return result
            else:
                raise RuntimeError("Unexpected length after splitting operands of this instruction: %s" % crashInstruction)
        else:
            failureReason = "Architecture is not supported."
        
        print("Unable to calculate crash address from instruction: %s " % crashInstruction, file=sys.stderr)
        print("Reason: %s" % failureReason, file=sys.stderr)
        return failureReason
    
    @staticmethod
    def calculateComplexDerefOpAddress(complexDerefOp, registerMap):
        
        match = re.match("((?:\\-?0x[0-9a-f]+)?)\\(%([a-z0-9]+),%([a-z0-9]+),([0-9]+)\\)", complexDerefOp)
        if match != None:
            offset = 0L
            if len(match.group(1)) > 0:
                offset = long(match.group(1), 16)
                
            regA = RegisterHelper.getRegisterValue(match.group(2), registerMap)
            regB = RegisterHelper.getRegisterValue(match.group(3), registerMap)
            
            mult = long(match.group(4), 16)
            
            # If we're missing any of the two register values, return None
            if regA == None or regB == None:
                if (regA == None):
                    return (None, "Missing value for register %s" % match.group(2))
                else:
                    return (None, "Missing value for register %s" % match.group(3))
            
            if RegisterHelper.getBitWidth(registerMap) == 32:
                val = int32(uint32(regA)) + int32(uint32(offset)) + (int32(uint32(regB)) * int32(uint32(mult)))
            else:
                # Assume 64 bit width
                val = int64(uint64(regA)) + int64(uint64(offset)) + (int64(uint64(regB)) * int64(uint64(mult)))
            return (long(val), None)
                
        return (None, "Unknown failure.")
