'''
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
import re
import unittest
from FTB import AssertionHelper

asanFFAbort = """Hit MOZ_CRASH() at /srv/repos/browser/mozilla-central/memory/mozalloc/mozalloc_abort.cpp:30
ASAN:SIGSEGV
=================================================================
==26289==ERROR: AddressSanitizer: SEGV on unknown address 0x000000000000 (pc 0x7fac9b54873a sp 0x7fff085f2120 bp 0x7fff085f2130 T0)
"""  # noqa

asanOverflow = """
==26403==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x60300021e6c8 at pc 0x7f30b3d276ef bp 0x7f30a521c8c0 sp 0x7f30a521c8b8
READ of size 8 at 0x60300021e6c8 thread T20 (MediaPlayback #1)
"""  # noqa

asanNegativeSize = """
==12549==ERROR: AddressSanitizer: negative-size-param: (size=-17179869184)
"""

asanStackOverflow = """
==9482==ERROR: AddressSanitizer: stack-overflow on address 0x7ffec10e9f58 (pc 0x0000004a5349 bp 0x7ffec10ea7b0 sp 0x7ffec10e9f60 T0)
"""  # noqa

jsshellMozCrash = """
Hit MOZ_CRASH(named lambda static scopes should have been skipped) at /srv/repos/mozilla-central/js/src/vm/ScopeObject.cpp:1277
"""  # noqa

jsSelfHostedAssert = """
Self-hosted JavaScript assertion info: "/srv/repos/mozilla-central/js/src/builtin/Intl.js:847: non-canonical BestAvailableLocale locale"
Assertion failure: false, at /srv/repos/mozilla-central/js/src/vm/SelfHosting.cpp:362
"""  # noqa

v8Abort = """
#
# Fatal error in ../src/compiler.cc, line 219
# Check failed: !feedback_vector_->metadata()->SpecDiffersFrom( literal()->feedback_vector_spec()).
#
"""

chakraAssert = """
ASSERTION 15887: (/srv/repos/ChakraCore/lib/Runtime/ByteCode/ByteCodeEmitter.cpp, line 4827) scope->HasInnerScopeIndex()
 Failure: (scope->HasInnerScopeIndex())
"""

windowsPathAssertFwdSlashes = """
Assertion failure: block->graph().osrBlock(), at c:/Users/fuzz1win/trees/mozilla-central/js/src/jit/Lowering.cpp:4691
"""

windowsPathAssertBwSlashes = r"""
Assertion failure: block->graph().osrBlock(), at c:\Users\fuzz1win\trees\mozilla-central\js\src\jit\Lowering.cpp:4691
"""

cppUnhandledException = """
terminate called after throwing an instance of 'std::regex_error'
  what():  regex_error
TEST-INFO | Main app process: killed by SIGIOT
"""

rustPanic1 = """
thread 'StyleThread#2' panicked at 'assertion failed: self.get_data().is_some()', /home/worker/workspace/build/src/servo/components/style/gecko/wrapper.rs:976"""  # noqa

rustPanic2 = """
thread 'RenderBackend' panicked at 'called `Option::unwrap()` on a `None` value', /checkout/src/libcore/option.rs:335:20"""  # noqa

rustPanic3 = """
thread '<unnamed>' panicked at 'assertion failed: `(left == right)`
  left: `Inline`,
 right: `Block`', /builds/worker/workspace/build/src/servo/components/style/style_adjuster.rs:352:8"""


class AssertionHelperTestASanFFAbort(unittest.TestCase):
    def runTest(self):
        err = asanFFAbort.splitlines()

        self.assertEqual(AssertionHelper.getAssertion(err), None)
        self.assertEqual(AssertionHelper.getAuxiliaryAbortMessage(err), None)


class AssertionHelperTestASanNegativeSize(unittest.TestCase):
    def runTest(self):
        err = asanNegativeSize.splitlines()

        self.assertEqual(AssertionHelper.getAssertion(err), None)
        assertMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAuxiliaryAbortMessage(err))
        expectedAssertMsg = r"ERROR: AddressSanitizer: negative\-size\-param: \(size=\-[0-9]{2,}\)"
        self.assertEqual(assertMsg, expectedAssertMsg)


class AssertionHelperTestASanStackOverflow(unittest.TestCase):
    def runTest(self):
        err = asanStackOverflow.splitlines()

        self.assertEqual(AssertionHelper.getAssertion(err), None)
        assertMsg = AssertionHelper.getAuxiliaryAbortMessage(err)
        expectedAssertMsg = "ERROR: AddressSanitizer: stack-overflow"
        self.assertEqual(assertMsg, expectedAssertMsg)


class AssertionHelperTestMozCrash(unittest.TestCase):
    def runTest(self):
        err = jsshellMozCrash.splitlines()

        sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
        expectedMsg = ("Hit MOZ_CRASH\\(named lambda static scopes should have been skipped\\) at "
                       "([a-zA-Z]:)?/.+/ScopeObject\\.cpp(:[0-9]+)+")

        self.assertEqual(sanitizedMsg, expectedMsg)


class AssertionHelperTestJSSelfHosted(unittest.TestCase):
    def runTest(self):
        err = jsSelfHostedAssert.splitlines()

        sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
        expectedMsg = ('Self\\-hosted JavaScript assertion info: "([a-zA-Z]:)?/.+/Intl\\.js(:[0-9]+)+: '
                       'non\\-canonical BestAvailableLocale locale"')

        self.assertEqual(sanitizedMsg, expectedMsg)


class AssertionHelperTestV8Abort(unittest.TestCase):
    def runTest(self):
        err = v8Abort.splitlines()

        sanitizedMsgs = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
        self.assertTrue(isinstance(sanitizedMsgs, list))
        self.assertEqual(len(sanitizedMsgs), 2)

        expectedMsgs = [
            "# Fatal error in \\.\\./src/compiler\\.cc, line [0-9]+",
            ("# Check failed: !feedback_vector_\\->metadata\\(\\)\\->SpecDiffersFrom\\( "
             "literal\\(\\)\\->feedback_vector_spec\\(\\)\\)\\.")
        ]

        self.assertEqual(sanitizedMsgs[0], expectedMsgs[0])
        self.assertEqual(sanitizedMsgs[1], expectedMsgs[1])


class AssertionHelperTestChakraAssert(unittest.TestCase):
    def runTest(self):
        err = chakraAssert.splitlines()

        sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
        expectedMsg = ('ASSERTION [0-9]{2,}: \\\\(([a-zA-Z]:)?/.+/ByteCodeEmitter\\.cpp, line [0-9]+\\) '
                       'scope\\->HasInnerScopeIndex\\(\\)')

        self.assertEqual(sanitizedMsg, expectedMsg)


class AssertionHelperTestWindowsPathSanitizing(unittest.TestCase):
    def runTest(self):
        err1 = windowsPathAssertFwdSlashes.splitlines()
        # err2 = windowsPathAssertBwSlashes.splitlines()

        assertionMsg1 = AssertionHelper.getAssertion(err1)
        # assertionMsg2 = AssertionHelper.getAssertion(err2)

        sanitizedMsg1 = AssertionHelper.getSanitizedAssertionPattern(assertionMsg1)
        # sanitizedMsg2 = AssertionHelper.getSanitizedAssertionPattern(assertionMsg2)

        expectedMsg = ("Assertion failure: block\\->graph\\(\\)\\.osrBlock\\(\\), at "
                       "([a-zA-Z]:)?/.+/Lowering\\.cpp(:[0-9]+)+")

        self.assertEqual(sanitizedMsg1, expectedMsg)

        # We currently don't support backward slashes, but if we add support, uncomment this test
        # self.assertEqual(sanitizedMsg2, expectedMsg)

        self.assertTrue(re.match(expectedMsg, assertionMsg1))

        # We currently don't support backward slashes, but if we add support, uncomment this test
        # self.assertTrue(re.match(expectedMsg, assertionMsg2))


class AssertionHelperTestAuxiliaryAbortASan(unittest.TestCase):
    def runTest(self):
        err = asanOverflow.splitlines()

        sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAuxiliaryAbortMessage(err))
        expectedMsg = [
            "ERROR: AddressSanitizer: heap\\-buffer\\-overflow",
            "READ of size 8 at 0x[0-9a-fA-F]+ thread T[0-9]{2,} \\(MediaPlayback #1\\)"
        ]

        self.assertEqual(sanitizedMsg, expectedMsg)


class AssertionHelperTestCPPUnhandledException(unittest.TestCase):
    def runTest(self):
        err = cppUnhandledException.splitlines()

        sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
        expectedMsg = "terminate called after throwing an instance of 'std::regex_error'"

        self.assertEqual(sanitizedMsg, expectedMsg)


class AssertionHelperTestRustPanic(unittest.TestCase):
    def test_01(self):
        err = rustPanic1.splitlines()
        sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
        expectedMsg = (r"thread 'StyleThread#[0-9]+' panicked at 'assertion failed: self\.get_data\(\)\.is_some\(\)', "
                       r"([a-zA-Z]:)?/.+/wrapper\.rs(:[0-9]+)+")
        self.assertEqual(sanitizedMsg, expectedMsg)

    def test_02(self):
        err = rustPanic2.splitlines()
        sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
        expectedMsg = (r"thread 'RenderBackend' panicked at 'called `Option::unwrap\(\)` on a `None` value', "
                       r"([a-zA-Z]:)?/.+/option\.rs(:[0-9]+)+")
        self.assertEqual(sanitizedMsg, expectedMsg)

    def test_03(self):
        err = rustPanic3.splitlines()
        sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
        self.assertEqual(len(sanitizedMsg), 3)
        self.assertEqual(sanitizedMsg[0], r"thread '<unnamed>' panicked at 'assertion failed: `\(left == right\)`")
        self.assertEqual(sanitizedMsg[-1], r" right: `Block`', ([a-zA-Z]:)?/.+/style_adjuster\.rs(:[0-9]+)+")


if __name__ == "__main__":
    unittest.main()
