'''
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
import unittest
import requests
import tempfile
import os

from requests.exceptions import ConnectionError
from Collector import Collector
import shutil
from FTB.Signatures.CrashInfo import CrashInfo
from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures.CrashSignature import CrashSignature

# Server and credentials (user/password) used for testing
testServerURL = "http://127.0.0.1:8000/rest/"
testAuthCreds = ("admin", "admin")

# Check if we have a remote server for testing, if not, skip tests
haveServer = True
try:
    requests.get(testServerURL)
except ConnectionError as e:
    haveServer = False
    
asanTraceCrash = """
ASAN:SIGSEGV
=================================================================
==5854==ERROR: AddressSanitizer: SEGV on unknown address 0x00000014 (pc 0x0810845f sp 0xffc57860 bp 0xffc57f18 T0)
    #0 0x810845e in js::AbstractFramePtr::asRematerializedFrame() const /srv/repos/mozilla-central/js/src/shell/../jit/RematerializedFrame.h:114
    #1 0x810845e in js::AbstractFramePtr::script() const /srv/repos/mozilla-central/js/src/shell/../vm/Stack-inl.h:572
    #2 0x810845e in EvalInFrame(JSContext*, unsigned int, JS::Value*) /srv/repos/mozilla-central/js/src/shell/js.cpp:2655
    #3 0x93f5b92 in js::CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), JS::CallArgs const&) /srv/repos/mozilla-central/js/src/jscntxtinlines.h:231
    #4 0x93f5b92 in js::Invoke(JSContext*, JS::CallArgs, js::MaybeConstruct) /srv/repos/mozilla-central/js/src/vm/Interpreter.cpp:484
    #5 0x9346ba7 in js::Invoke(JSContext*, JS::Value const&, JS::Value const&, unsigned int, JS::Value const*, JS::MutableHandle<JS::Value>) /srv/repos/mozilla-central/js/src/vm/Interpreter.cpp:540
    #6 0x8702baa in js::jit::DoCallFallback(JSContext*, js::jit::BaselineFrame*, js::jit::ICCall_Fallback*, unsigned int, JS::Value*, JS::MutableHandle<JS::Value>) /srv/repos/mozilla-central/js/src/jit/BaselineIC.cpp:8638

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV /srv/repos/mozilla-central/js/src/shell/../jit/RematerializedFrame.h:114 js::AbstractFramePtr::asRematerializedFrame() const
==5854==ABORTING
"""

exampleTestCase = '''function init() {
    while ( {}, this) !(Object === "Infinity");      
}
eval("init()");
'''

@unittest.skipIf(not haveServer, reason="No remote server available for testing")
class TestCollectorSubmit(unittest.TestCase):
    def setUp(self):
        self.url = testServerURL + "crashes/"
        self.tmpCacheDir = tempfile.mkdtemp(prefix="collector-tmp-")
        
    def tearDown(self):
        shutil.rmtree(self.tmpCacheDir)
        
    def getRemoteCrashEntryCount(self):
        response = requests.get(self.url, auth=testAuthCreds)
        return len(response.json())
        
    def runTest(self):
        collector = Collector(self.tmpCacheDir, 
                              serverHost='127.0.0.1', 
                              serverPort='8000',
                              serverProtocol='http',
                              serverUser=testAuthCreds[0],
                              serverPass=testAuthCreds[1],  
                              clientId='test-fuzzer1')
        
        config = ProgramConfiguration("mozilla-central", "x86-64", "linux", version="ba0bc4f26681")
        crashInfo = CrashInfo.fromRawCrashData([], asanTraceCrash.splitlines(), config)
        
        # TODO: This is only a rudimentary check to see if we submitted *something*.
        # We should check more precisely that the information submitted is correct.
        issueCount = self.getRemoteCrashEntryCount()
        collector.submit(crashInfo, exampleTestCase)
        self.assertEqual(self.getRemoteCrashEntryCount(), issueCount + 1)
        
@unittest.skipIf(not haveServer, reason="No remote server available for testing")
class TestCollectorRefresh(unittest.TestCase):
    def setUp(self):
        self.tmpCacheDir = tempfile.mkdtemp(prefix="collector-tmp-")
        
    def tearDown(self):
        shutil.rmtree(self.tmpCacheDir)
        
    def runTest(self):
        collector = Collector(self.tmpCacheDir, 
                              serverHost='127.0.0.1', 
                              serverPort='8000',
                              serverProtocol='http',
                              serverUser=testAuthCreds[0],
                              serverPass=testAuthCreds[1],  
                              clientId='test-fuzzer1')
        
        collector.refresh()
        
        receivedSignatures = False
        
        for sigFile in os.listdir(self.tmpCacheDir):
            receivedSignatures = True
            CrashSignature.fromFile(os.path.join(self.tmpCacheDir, sigFile))
        
        if not receivedSignatures:
            self.skipTest("Server did not provide signatures")


if __name__ == "__main__":
    unittest.main()
