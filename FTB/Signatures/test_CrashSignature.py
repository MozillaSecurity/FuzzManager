'''
Created on Oct 9, 2014

@author: decoder
'''
import unittest
from FTB.Signatures.CrashInfo import CrashInfo
import json

testTrace1 = """Program received signal SIGSEGV, Segmentation fault.
GetObjectAllocKindForCopy (obj=0x7ffff54001b0, nursery=...) at /srv/repos/mozilla-central/js/src/gc/Nursery.cpp:369
369         if (obj->is<ArrayObject>()) {
#0  GetObjectAllocKindForCopy (obj=0x7ffff54001b0, nursery=...) at /srv/repos/mozilla-central/js/src/gc/Nursery.cpp:369
#1  js::Nursery::moveToTenured (this=0x1673be0, trc=0x7fffffffa2d0, src=<optimized out>) at /srv/repos/mozilla-central/js/src/gc/Nursery.cpp:570
#2  0x00000000004d167a in MinorGCCallback (thingp=0x7fffffff9fd0, jstrc=<optimized out>, kind=<optimized out>) at /srv/repos/mozilla-central/js/src/gc/Nursery.cpp:721
#3  js::Nursery::MinorGCCallback (jstrc=<optimized out>, thingp=0x7fffffff9fd0, kind=<optimized out>) at /srv/repos/mozilla-central/js/src/gc/Nursery.cpp:717
#4  0x00000000004b8690 in MarkInternal<JSObject> (trc=0x7fffffffa2d0, thingp=<optimized out>) at /srv/repos/mozilla-central/js/src/gc/Marking.cpp:317
#5  0x00000000004cc55e in MarkValueInternal (v=0x7fffffffa5d8, trc=0x7fffffffa2d0) at /srv/repos/mozilla-central/js/src/gc/Marking.cpp:804
#6  MarkValueInternal (v=0x7fffffffa5d8, trc=0x7fffffffa2d0) at /srv/repos/mozilla-central/js/src/gc/Marking.cpp:827
#7  js::gc::MarkValueRoot (trc=<optimized out>, v=0x7fffffffa5d8, name=<optimized out>) at /srv/repos/mozilla-central/js/src/gc/Marking.cpp:831
rax     0x2b2b2b2b      3110627432037296939
rbx     0xf54001b0      140737308000688
rcx     0xbad0bad1      3134241489
rdx     0x1656120       23421216
rsi     0xffffa2d0      140737488331472
rdi     0x1673be0       23542752
rbp     0xf54001b0      140737308000688
rsp     0xffff9f10      140737488330512
r8      0x0     0
r9      0x0     0
r10     0x1     1
r11     0x1     1
r12     0x0     -1266637395197952
r13     0xffffa2d0      140737488331472
r14     0x1673be0       23542752
r15     0x201   513
rip     0x4d0b32 <js::Nursery::moveToTenured(js::gc::MinorCollectionTracer*, JSObject*)+34>
=> 0x4d0b32 <js::Nursery::moveToTenured(js::gc::MinorCollectionTracer*, JSObject*)+34>: mov    (%rax),%r8
"""

testSignature1 = '''{"symptoms": [
    {
    "functionName": "GetObjectAllocKindForCopy",
    "frameNumber": 0,
    "type": "stackFrame"
  },
    {
    "functionName": "js::Nursery::moveToTenured",
    "frameNumber": 1,
    "type": "stackFrame"
  },
    {
    "functionName": "MinorGCCallback",
    "frameNumber": 2,
    "type": "stackFrame"
  },
    {
    "functionName": "js::Nursery::MinorGCCallback",
    "frameNumber": 3,
    "type": "stackFrame"
  },
    {
    "address": "0x2b2b2b2b",
    "type": "crashAddress"
  }
]}
'''

testSignature2 = '''{"symptoms": [
    {
    "functionName": "GetObjectAllocKindForCopy",
    "frameNumber": 0,
    "type": "stackFrame"
  },
    {
    "functionName": "js::Nursery::moveToTenured",
    "frameNumber": 1,
    "type": "stackFrame"
  },
    {
    "functionName": "MinorGCCallback",
    "frameNumber": 2,
    "type": "stackFrame"
  }
]}
'''

testSignature3 = '''{"symptoms": [
    {
    "functionName": "GetObjectAllocKindForCopy",
    "frameNumber": 0,
    "type": "stackFrame"
  },
    {
    "functionName": "js::Nursery::moveToTenured",
    "frameNumber": 1,
    "type": "stackFrame"
  },
  {
    "address": "0x2b2b2b2b",
    "type": "crashAddress"
  },
    {
    "type": "instruction",
    "instructionName": "mov    (%rax),%r8"
  }
]}
'''

class SignatureCreateTest(unittest.TestCase):


    def runTest(self):
        crashInfo = CrashInfo.fromRawCrashData([], [], testTrace1.splitlines())
        crashSig1 = crashInfo.createCrashSignature(forceCrashAddress=True, maxFrames=4)
        crashSig2 = crashInfo.createCrashSignature(forceCrashAddress=False, maxFrames=3)
        crashSig3 = crashInfo.createCrashSignature(forceCrashInstruction=True, maxFrames=2)

        # Check that all generated signatures match their originating crashInfo
        self.assert_(crashSig1.matches(crashInfo))
        self.assert_(crashSig2.matches(crashInfo))
        self.assert_(crashSig3.matches(crashInfo))
        
        # Check that the generated signatures look as expected
        self.assertEqual(json.loads(str(crashSig1)), json.loads(testSignature1))
        self.assertEqual(json.loads(str(crashSig2)), json.loads(testSignature2))
        
        #  The third crashInfo misses 2 frames from the top 4 frames, so it will
        #  also include the crash address, even though we did not request it.
        self.assertEqual(json.loads(str(crashSig3)), json.loads(testSignature3))
        

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()