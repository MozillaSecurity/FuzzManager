"""
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""

import re
from pathlib import Path

from FTB import AssertionHelper

FIXTURE_PATH = Path(__file__).parent / "fixtures"


def _check_regex_matches(error_lines, sanitized_message):
    if isinstance(sanitized_message, (str, bytes)):
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
    raise AssertionError(
        f"sanitized message did not match input: {sanitized_message!r}"
    )


def test_AssertionHelperTestASanFFAbort():
    err = (FIXTURE_PATH / "assert_asan_ff_abort.txt").read_text().splitlines()

    assert AssertionHelper.getAssertion(err) is None
    assert AssertionHelper.getAuxiliaryAbortMessage(err) is None


def test_AssertionHelperTestASanNegativeSize():
    err = (FIXTURE_PATH / "assert_asan_negative_size.txt").read_text().splitlines()

    assert AssertionHelper.getAssertion(err) is None
    assertMsg = AssertionHelper.getSanitizedAssertionPattern(
        AssertionHelper.getAuxiliaryAbortMessage(err)
    )
    expectedAssertMsg = (
        r"ERROR: AddressSanitizer: negative-size-param: \(size=-[0-9]{2,}\)"
    )
    assert assertMsg == expectedAssertMsg


def test_AssertionHelperTestASanStackOverflow():
    err = (FIXTURE_PATH / "assert_asan_stack_overflow.txt").read_text().splitlines()

    assert AssertionHelper.getAssertion(err) is None
    assertMsg = AssertionHelper.getAuxiliaryAbortMessage(err)
    expectedAssertMsg = "ERROR: AddressSanitizer: stack-overflow"
    assert assertMsg == expectedAssertMsg


def test_AssertionHelperTestMozCrash():
    err = (FIXTURE_PATH / "assert_jsshell_moz_crash.txt").read_text().splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(
        AssertionHelper.getAssertion(err)
    )
    expectedMsg = (
        r"Hit MOZ_CRASH\(named lambda static scopes should have been skipped\) at "
        r"([a-zA-Z]:)?/.+/ScopeObject\.cpp(:[0-9]+)+"
    )
    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestMozCrashMultiLine():
    err = (FIXTURE_PATH / "assert_moz_crash_multiline.txt").read_text().splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(
        AssertionHelper.getAssertion(err)
    )
    assert sanitizedMsg[0] == (
        r"Hit MOZ_CRASH\(assertion failed:"
        r" combined_local_clip_rect\.size\.width >= 0\.0 &&"
    )
    assert sanitizedMsg[-1] == (
        r"    combined_local_clip_rect\.size\.height >= 0\.0\)"
        r" at gfx/wr/webrender/src/prim_store/mod\.rs(:[0-9]+)+"
    )
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestMozCrashWithPath():
    err = (FIXTURE_PATH / "assert_moz_crash_with_path.txt").read_text().splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(
        AssertionHelper.getAssertion(err)
    )
    expectedMsg = (
        r"Hit MOZ_CRASH\(([a-zA-Z]:)?/.+/celt_decoder\.c(:[0-9]+)+ assertion failed: "
        r"st->start < st->end\) at nil(:[0-9]+)+"
    )
    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestMultiMozCrash():
    err = (FIXTURE_PATH / "assert_moz_crash_multi.txt").read_text().splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(
        AssertionHelper.getAssertion(err)
    )
    expectedMsg = (
        r"Hit MOZ_CRASH\(good message\) at "
        r"([a-zA-Z]:)?/.+/spatial_node\.rs(:[0-9]+)+"
    )
    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestJSSelfHosted():
    err = (
        (FIXTURE_PATH / "assert_jsshell_self_hosted_assert.txt")
        .read_text()
        .splitlines()
    )

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(
        AssertionHelper.getAssertion(err)
    )
    expectedMsg = (
        r'Self-hosted JavaScript assertion info: "([a-zA-Z]:)?/.+/Intl\.js(:[0-9]+)+: '
        r'non-canonical BestAvailableLocale locale"'
    )

    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestV8Abort():
    err = (FIXTURE_PATH / "assert_v8_abort.txt").read_text().splitlines()

    sanitizedMsgs = AssertionHelper.getSanitizedAssertionPattern(
        AssertionHelper.getAssertion(err)
    )
    assert isinstance(sanitizedMsgs, list)
    assert len(sanitizedMsgs) == 2

    expectedMsgs = [
        r"# Fatal error in \.\./src/compiler\.cc, line [0-9]+",
        (
            r"# Check failed: !feedback_vector_->metadata\(\)->SpecDiffersFrom\( "
            r"literal\(\)->feedback_vector_spec\(\)\)\."
        ),
    ]

    assert sanitizedMsgs == expectedMsgs
    _check_regex_matches(err, sanitizedMsgs)


def test_AssertionHelperTestChakraAssert():
    err = (FIXTURE_PATH / "assert_chakra_assert.txt").read_text().splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(
        AssertionHelper.getAssertion(err)
    )
    expectedMsg = (
        r"ASSERTION [0-9]{2,}: \(([a-zA-Z]:)?/.+/ByteCodeEmitter\.cpp, line [0-9]+\) "
        r"scope->HasInnerScopeIndex\(\)"
    )

    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestWindowsPathSanitizing():
    err1 = (
        (FIXTURE_PATH / "assert_windows_forward_slash_path.txt")
        .read_text()
        .splitlines()
    )
    err2 = (
        (FIXTURE_PATH / "assert_windows_back_slash_path.txt").read_text().splitlines()
    )

    assertionMsg1 = AssertionHelper.getAssertion(err1)
    assertionMsg2 = AssertionHelper.getAssertion(err2)

    sanitizedMsg1 = AssertionHelper.getSanitizedAssertionPattern(assertionMsg1)
    sanitizedMsg2 = AssertionHelper.getSanitizedAssertionPattern(assertionMsg2)

    expectedMsg = (
        r"Assertion failure: block->graph\(\)\.osrBlock\(\), at "
        r"([a-zA-Z]:)?/.+/Lowering\.cpp(:[0-9]+)+"
    )

    assert sanitizedMsg1 == expectedMsg
    assert sanitizedMsg2 == expectedMsg
    _check_regex_matches(err1, sanitizedMsg1)

    # Backslash support is two-part:
    # 1. generate unix-style path patterns for windows paths (will not match using regex
    #    directly)
    # 2. modify StringMatch to replace backslash with forward slash for matching (so
    #    unix patterns will match windows paths)
    #
    # That means a test for this can't work at this level
    # _check_regex_matches(err2, sanitizedMsg2)


def test_AssertionHelperTestAuxiliaryAbortASan():
    err = (
        (FIXTURE_PATH / "assert_asan_heap_buffer_overflow.txt").read_text().splitlines()
    )

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(
        AssertionHelper.getAuxiliaryAbortMessage(err)
    )
    expectedMsg = [
        r"ERROR: AddressSanitizer: heap-buffer-overflow",
        r"READ of size 8 at 0x[0-9a-fA-F]+ thread T[0-9]{2,} \(MediaPlayback #1\)",
    ]

    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestCPPUnhandledException():
    err = (FIXTURE_PATH / "assert_cpp_unhandled_exception.txt").read_text().splitlines()

    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(
        AssertionHelper.getAssertion(err)
    )
    expectedMsg = "terminate called after throwing an instance of 'std::regex_error'"

    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestRustPanic01():
    err = (FIXTURE_PATH / "assert_rust_panic1.txt").read_text().splitlines()
    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(
        AssertionHelper.getAssertion(err)
    )
    expectedMsg = (
        r"thread 'StyleThread#[0-9]+' panicked at "
        r"'assertion failed: self\.get_data\(\)\.is_some\(\)', "
        r"([a-zA-Z]:)?/.+/wrapper\.rs(:[0-9]+)+"
    )

    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestRustPanic02():
    err = (FIXTURE_PATH / "assert_rust_panic2.txt").read_text().splitlines()
    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(
        AssertionHelper.getAssertion(err)
    )
    expectedMsg = (
        r"thread 'RenderBackend' panicked at 'called `Option::unwrap\(\)` "
        r"on a `None` value', ([a-zA-Z]:)?/.+/option\.rs(:[0-9]+)+"
    )

    assert sanitizedMsg == expectedMsg
    _check_regex_matches(err, sanitizedMsg)


def test_AssertionHelperTestRustPanic03():
    err = (FIXTURE_PATH / "assert_rust_panic3.txt").read_text().splitlines()
    sanitizedMsg = AssertionHelper.getSanitizedAssertionPattern(
        AssertionHelper.getAssertion(err)
    )

    assert len(sanitizedMsg) == 3
    assert (
        sanitizedMsg[0]
        == r"thread '<unnamed>' panicked at 'assertion failed: `\(left == right\)`"
    )
    assert (
        sanitizedMsg[-1]
        == r" right: `Block`', ([a-zA-Z]:)?/.+/style_adjuster\.rs(:[0-9]+)+"
    )
    _check_regex_matches(err, sanitizedMsg)
