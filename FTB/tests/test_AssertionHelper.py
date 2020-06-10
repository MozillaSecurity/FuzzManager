# coding: utf-8
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
import six
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

mozCrashMultiLine = """
Hit MOZ_CRASH(assertion failed: combined_local_clip_rect.size.width >= 0.0 &&
    combined_local_clip_rect.size.height >= 0.0) at gfx/wr/webrender/src/prim_store/mod.rs:2198
"""  # noqa

mozCrashWithPath = "Hit MOZ_CRASH(/builds/worker/workspace/build/src/media/libopus/celt/celt_decoder.c:125 assertion failed: st->start < st->end) at nil:16"  # noqa

multiMozCrash = """
Hit MOZ_CRASH(good message) at /builds/worker/workspace/build/src/gfx/webrender/src/spatial_node.rs:428
#01: ???[/home/ubuntu/firefox/libxul.so +0x46d7415]
Hit MOZ_CRASH(Aborting on channel error.) at /builds/worker/workspace/build/src/ipc/glue/MessageChannel.cpp:2658
#01: ???[/home/ubuntu/firefox/libxul.so +0x10ead39]
"""  # noqa


def _check_regex_matches(error_lines, sanitized_message):
    if isinstance(sanitized_message, (six.text_type, bytes)):
        sanitized_message = [sanitized_message]
    else:
        sanitized_message = list(sanitized_message)

    # Ensure regex matches original message
    for line in error_lines:
        for idx, pattern in enumerate(sanitized_message):
            if re.search(pattern, line) is not None:
                sanitized_message.pop(idx)
                break
        if not sanitized_message:
            return
    raise AssertionError("sanitized message did not match input: %r" % (sanitized_message,))


def test_AssertionHelperTestASanFFAbort():
    err = asanFFAbort.splitlines()

    assert AssertionHelper.getAssertion(err) is None
    assert AssertionHelper.getAuxiliaryAbortMessage(err) is None


def test_AssertionHelperTestASanNegativeSize():
    err = asanNegativeSize.splitlines()

    assert AssertionHelper.getAssertion(err) is None
    assertMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAuxiliaryAbortMessage(err))
    expectedAssertMsg = r"ERROR: AddressSanitizer: negative-size-param: \(size=-[0-9]{2,}\)"
    assert assertMsg == expectedAssertMsg


def test_AssertionHelperTestASanStackOverflow():
    err = asanStackOverflow.splitlines()

    assert AssertionHelper.getAssertion(err) is None
    assertMsg = AssertionHelper.getAuxiliaryAbortMessage(err)
    expectedAssertMsg = "ERROR: AddressSanitizer: stack-overflow"
    assert assertMsg == expectedAssertMsg


def test_AssertionHelperTestMozCrash():
    err = jsshellMozCrash.splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
    expectedMsg = (r"Hit MOZ_CRASH\(named lambda static scopes should have been skipped\) at "
                   r"([a-zA-Z]:)?/.+/ScopeObject\.cpp(:[0-9]+)+")
    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestMozCrashMultiLine():
    err = mozCrashMultiLine.splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
    assert sanitizedMsg[0] == (r"Hit MOZ_CRASH\(assertion failed:"
                               r" combined_local_clip_rect\.size\.width >= 0\.0 &&")
    assert sanitizedMsg[-1] == (r"    combined_local_clip_rect\.size\.height >= 0\.0\)"
                                r" at gfx/wr/webrender/src/prim_store/mod\.rs(:[0-9]+)+")
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestMozCrashWithPath():
    err = mozCrashWithPath.splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
    expectedMsg = (r"Hit MOZ_CRASH\(([a-zA-Z]:)?/.+/celt_decoder\.c(:[0-9]+)+ assertion failed: "
                   r"st->start < st->end\) at nil(:[0-9]+)+")
    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestMultiMozCrash():
    err = multiMozCrash.splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
    expectedMsg = (r"Hit MOZ_CRASH\(good message\) at "
                   r"([a-zA-Z]:)?/.+/spatial_node\.rs(:[0-9]+)+")
    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestJSSelfHosted():
    err = jsSelfHostedAssert.splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
    expectedMsg = (r'Self-hosted JavaScript assertion info: "([a-zA-Z]:)?/.+/Intl\.js(:[0-9]+)+: '
                   r'non-canonical BestAvailableLocale locale"')

    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestV8Abort():
    err = v8Abort.splitlines()

    sanitizedMsgs = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
    assert isinstance(sanitizedMsgs, list)
    assert len(sanitizedMsgs) == 2

    expectedMsgs = [
        r"# Fatal error in \.\./src/compiler\.cc, line [0-9]+",
        (r"# Check failed: !feedback_vector_->metadata\(\)->SpecDiffersFrom\( "
         r"literal\(\)->feedback_vector_spec\(\)\)\.")
    ]

    assert sanitizedMsgs == expectedMsgs
    _check_regex_matches(err, sanitizedMsgs)


def test_AssertionHelperTestChakraAssert():
    err = chakraAssert.splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
    expectedMsg = (r'ASSERTION [0-9]{2,}: \(([a-zA-Z]:)?/.+/ByteCodeEmitter\.cpp, line [0-9]+\) '
                   r'scope->HasInnerScopeIndex\(\)')

    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestWindowsPathSanitizing():
    err1 = windowsPathAssertFwdSlashes.splitlines()
    err2 = windowsPathAssertBwSlashes.splitlines()

    assertionMsg1 = AssertionHelper.getAssertion(err1)
    assertionMsg2 = AssertionHelper.getAssertion(err2)

    sanitizedMsg1 = AssertionHelper.getSanitizedAssertionPattern(assertionMsg1)
    sanitizedMsg2 = AssertionHelper.getSanitizedAssertionPattern(assertionMsg2)

    expectedMsg = (r"Assertion failure: block->graph\(\)\.osrBlock\(\), at "
                   r"([a-zA-Z]:)?/.+/Lowering\.cpp(:[0-9]+)+")

    assert sanitizedMsg1 == expectedMsg
    assert sanitizedMsg2 == expectedMsg
    _check_regex_matches(err1, sanitizedMsg1)

    # Backslash support is two-part:
    # 1. generate unix-style path patterns for windows paths (will not match using regex directly)
    # 2. modify StringMatch to replace backslash with forward slash for matching (so unix patterns will match
    #    windows paths)
    #
    # That means a test for this can't work at this level
    #_check_regex_matches(err2, sanitizedMsg2)


def test_AssertionHelperTestAuxiliaryAbortASan():
    err = asanOverflow.splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAuxiliaryAbortMessage(err))
    expectedMsg = [
        r"ERROR: AddressSanitizer: heap-buffer-overflow",
        r"READ of size 8 at 0x[0-9a-fA-F]+ thread T[0-9]{2,} \(MediaPlayback #1\)"
    ]

    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestCPPUnhandledException():
    err = cppUnhandledException.splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
    expectedMsg = "terminate called after throwing an instance of 'std::regex_error'"

    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestRustPanic01():
    err = rustPanic1.splitlines()
    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
    expectedMsg = (r"thread 'StyleThread#[0-9]+' panicked at 'assertion failed: self\.get_data\(\)\.is_some\(\)', "
                   r"([a-zA-Z]:)?/.+/wrapper\.rs(:[0-9]+)+")

    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestRustPanic02():
    err = rustPanic2.splitlines()
    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))
    expectedMsg = (r"thread 'RenderBackend' panicked at 'called `Option::unwrap\(\)` on a `None` value', "
                   r"([a-zA-Z]:)?/.+/option\.rs(:[0-9]+)+")

    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestRustPanic03():
    err = rustPanic3.splitlines()
    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(AssertionHelper.getAssertion(err))

    assert len(sanitizedMsg) == 3
    assert sanitizedMsg[0] == r"thread '<unnamed>' panicked at 'assertion failed: `\(left == right\)`"
    assert sanitizedMsg[-1] == r" right: `Block`', ([a-zA-Z]:)?/.+/style_adjuster\.rs(:[0-9]+)+"
    _check_regex_matches(err, sanitizedMsg)
