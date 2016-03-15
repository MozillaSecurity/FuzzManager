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

asanFFAbort = """Hit MOZ_CRASH() at /srv/repos/browser/mozilla-central/memory/mozalloc/mozalloc_abort.cpp:30
ASAN:SIGSEGV
=================================================================
==26289==ERROR: AddressSanitizer: SEGV on unknown address 0x000000000000 (pc 0x7fac9b54873a sp 0x7fff085f2120 bp 0x7fff085f2130 T0)
"""

jsshellMozCrash = """
Hit MOZ_CRASH(named lambda static scopes should have been skipped) at /srv/repos/mozilla-central/js/src/vm/ScopeObject.cpp:1277
"""

v8Abort = """
#
# Fatal error in ../src/compiler.cc, line 219
# Check failed: !feedback_vector_->metadata()->SpecDiffersFrom( literal()->feedback_vector_spec()).
#
"""

class AssertionHelperTestASanFFAbort(unittest.TestCase):
    def runTest(self):
        err = asanFFAbort.splitlines()

        self.assertIn("AddressSanitizer", AssertionHelper.getAssertion(err, False))

        # Now check that ASan crash message is not used if only programmatic assertions are requested
        self.assertEqual(AssertionHelper.getAssertion(err, True), None)

class AssertionHelperTestSanitizing(unittest.TestCase):
    def runTest(self):
        err = asanFFAbort.splitlines()

        sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err, False))
        expectedMsg = "==[0-9]{2,}==ERROR: AddressSanitizer: SEGV on unknown address 0x[0-9a-fA-F]+ \\(pc 0x[0-9a-fA-F]+ sp 0x[0-9a-fA-F]+ bp 0x[0-9a-fA-F]+ T0\\)"

        self.assertEqual(sanitizedMsg, expectedMsg)

class AssertionHelperTestMozCrash(unittest.TestCase):
    def runTest(self):
        err = jsshellMozCrash.splitlines()

        sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err, False))
        expectedMsg = "Hit MOZ_CRASH\\(named lambda static scopes should have been skipped\\) at /.+/ScopeObject\\.cpp:[0-9]+"

        self.assertEqual(sanitizedMsg, expectedMsg)

class AssertionHelperTestV8Abort(unittest.TestCase):
    def runTest(self):
        err = v8Abort.splitlines()

        sanitizedMsgs = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err, False))
        self.assertTrue(isinstance(sanitizedMsgs, list))
        self.assertEqual(len(sanitizedMsgs), 2)

        expectedMsgs = [
                         "# Fatal error in \\.\\./src/compiler\\.cc, line [0-9]+",
                         "# Check failed: !feedback_vector_\\->metadata\\(\\)\\->SpecDiffersFrom\\( literal\\(\\)\\->feedback_vector_spec\\(\\)\\)\\."
        ]

        self.assertEqual(sanitizedMsgs[0], expectedMsgs[0])
        self.assertEqual(sanitizedMsgs[1], expectedMsgs[1])

if __name__ == "__main__":
    unittest.main()
