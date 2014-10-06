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
from FTB import AssertionHelper

asanFFAbort = """
[26289] ###!!! ASSERTION: Unexpected non-ASCII character: '!(*s2 & ~0x7F)', file ../../../dist/include/nsCharTraits.h, line 168
Hit MOZ_CRASH() at /srv/repos/browser/mozilla-central/memory/mozalloc/mozalloc_abort.cpp:30
ASAN:SIGSEGV
=================================================================
==26289==ERROR: AddressSanitizer: SEGV on unknown address 0x000000000000 (pc 0x7fac9b54873a sp 0x7fff085f2120 bp 0x7fff085f2130 T0)
"""

class AssertionHelperTestASanFFAbort(unittest.TestCase):
    def runTest(self):
        err = asanFFAbort.splitlines()
        
        # Check that the assertion is preferred to the ASan crash message,
        # and that the PID tag at the beginning of the line is stripped
        assert AssertionHelper.getAssertion(err, False).startswith("###!!! ASSERTION")
        
        # Now check that the ASan crash message is used if no assertion is present
        err.pop(0)
        assert AssertionHelper.getAssertion(err, False).find("AddressSanitizer") != -1
        
        # Now check that ASan crash message is not used if only programmatic assertions are requested
        assert AssertionHelper.getAssertion(err, True) == None
        
if __name__ == "__main__":
    unittest.main()