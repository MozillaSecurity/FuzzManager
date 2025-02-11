"""
Created on Oct 9, 2014

@author: decoder
"""

import json
from pathlib import Path

from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures.CrashInfo import CrashInfo
from FTB.Signatures.CrashSignature import CrashSignature
from FTB.Signatures.Matchers import StringMatch
from FTB.Signatures.Symptom import OutputSymptom, StackFramesSymptom

FIXTURE_PATH = Path(__file__).parent / "fixtures"


def test_SignatureCreateTest():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_1.txt").read_text().splitlines(),
    )

    crashSig1 = crashInfo.createCrashSignature(
        forceCrashAddress=True, maxFrames=4, minimumSupportedVersion=10
    )
    crashSig2 = crashInfo.createCrashSignature(
        forceCrashAddress=False, maxFrames=3, minimumSupportedVersion=10
    )
    crashSig3 = crashInfo.createCrashSignature(
        forceCrashInstruction=True, maxFrames=2, minimumSupportedVersion=10
    )

    # Check that all generated signatures match their originating crashInfo
    assert crashSig1.matches(crashInfo)
    assert crashSig2.matches(crashInfo)
    assert crashSig3.matches(crashInfo)

    # Check that the generated signatures look as expected
    with (FIXTURE_PATH / "sig_test_1.json").open() as f:
        assert json.loads(str(crashSig1)) == json.load(f)
    with (FIXTURE_PATH / "sig_test_2.json").open() as f:
        assert json.loads(str(crashSig2)) == json.load(f)

    #  The third crashInfo misses 2 frames from the top 4 frames, so it will
    #  also include the crash address, even though we did not request it.
    with (FIXTURE_PATH / "sig_test_3.json").open() as f:
        assert json.loads(str(crashSig3)) == json.load(f)


def test_SignatureTestCaseMatchTest():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_1.txt").read_text().splitlines(),
    )

    testSig3 = CrashSignature((FIXTURE_PATH / "sig_test_3.json").read_text())
    testSig4 = CrashSignature((FIXTURE_PATH / "sig_test_4.json").read_text())
    testSig5 = CrashSignature((FIXTURE_PATH / "sig_test_5.json").read_text())
    testSig6 = CrashSignature((FIXTURE_PATH / "sig_test_6.json").read_text())

    assert not testSig3.matchRequiresTest()
    assert testSig4.matchRequiresTest()
    assert testSig5.matchRequiresTest()

    # Must not match without testcase provided
    assert not testSig4.matches(crashInfo)
    assert not testSig5.matches(crashInfo)
    assert not testSig6.matches(crashInfo)

    # Attach testcase
    crashInfo.testcase = (FIXTURE_PATH / "testcase_1.js").read_text()

    # Must match with testcase provided
    assert testSig4.matches(crashInfo)
    assert testSig5.matches(crashInfo)

    # This one does not match at all
    assert not testSig6.matches(crashInfo)


def test_SignatureStackFramesTest():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_1.txt").read_text().splitlines(),
    )

    testSig1 = CrashSignature(
        (FIXTURE_PATH / "sig_test_stack_frames_1.json").read_text()
    )
    testSig2 = CrashSignature(
        (FIXTURE_PATH / "sig_test_stack_frames_2.json").read_text()
    )
    testSig3 = CrashSignature(
        (FIXTURE_PATH / "sig_test_stack_frames_3.json").read_text()
    )
    testSig4 = CrashSignature(
        (FIXTURE_PATH / "sig_test_stack_frames_4.json").read_text()
    )
    testSig5 = CrashSignature(
        (FIXTURE_PATH / "sig_test_stack_frames_5.json").read_text()
    )

    assert testSig1.matches(crashInfo)
    assert testSig2.matches(crashInfo)
    assert testSig3.matches(crashInfo)
    assert testSig4.matches(crashInfo)
    assert not testSig5.matches(crashInfo)


def test_SignatureStackFramesAlgorithmsTest():
    # Do some direct matcher tests on edge cases
    assert StackFramesSymptom._match([], [StringMatch("???")])
    assert not StackFramesSymptom._match([], [StringMatch("???"), StringMatch("a")])

    # Test the diff algorithm, test array contains:
    # stack, signature, expected distance, proposed signature
    testArray = [
        (
            ["a", "b", "x", "a", "b", "c"],
            ["a", "b", "???", "a", "b", "x", "c"],
            1,
            ["a", "b", "???", "a", "b", "?", "c"],
        ),
        (
            ["b", "x", "a", "b", "c"],
            ["a", "b", "???", "a", "b", "x", "c"],
            2,
            ["?", "b", "???", "a", "b", "?", "c"],
        ),
        (
            ["b", "x", "a", "d", "x"],
            ["a", "b", "???", "a", "b", "x", "c"],
            3,
            ["?", "b", "???", "a", "?", "x", "?"],
        ),
    ]

    for stack, rawSig, expectedDepth, expectedSig in testArray:
        for maxDepth in (expectedDepth, 3):
            (actualDepth, actualSig) = StackFramesSymptom._diff(
                stack, [StringMatch(x) for x in rawSig], 0, 1, maxDepth
            )
            assert expectedDepth == actualDepth
            assert expectedSig == [str(x) for x in actualSig]


def test_SignaturePCREShortTest():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_1.txt").read_text().splitlines(),
    )

    testSig1 = CrashSignature((FIXTURE_PATH / "sig_test_pcre_short_1.json").read_text())
    testSig2 = CrashSignature((FIXTURE_PATH / "sig_test_pcre_short_2.json").read_text())

    assert testSig1.matches(crashInfo)
    assert not testSig2.matches(crashInfo)


def test_SignatureStackFramesWildcardTailTest():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_2.txt").read_text().splitlines(),
    )

    testSig = crashInfo.createCrashSignature()

    # Ensure that the last frame with a symbol is at the right place and there is
    # nothing else, especially no wildcard, following afterwards.
    assert isinstance(testSig.symptoms[0], StackFramesSymptom)
    assert (
        str(testSig.symptoms[0].functionNames[6])
        == "js::jit::CheckOverRecursedWithExtra"
    )
    assert len(testSig.symptoms[0].functionNames) == 7


def test_SignatureStackFramesRegressionTest():
    config = ProgramConfiguration("test", "x86", "linux")
    crashInfoNeg = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_heap_with_crash_address.txt")
        .read_text()
        .splitlines(),
    )
    crashInfoPos = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_heap_without_crash_address.txt")
        .read_text()
        .splitlines(),
    )

    testSigEmptyCrashAddress = CrashSignature(
        (FIXTURE_PATH / "sig_test_empty_crash_address.json").read_text()
    )

    assert testSigEmptyCrashAddress.matches(crashInfoPos)
    assert not testSigEmptyCrashAddress.matches(crashInfoNeg)


def test_SignatureStackFramesAuxMessagesTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfoPos = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_with_aux_message.txt")
        .read_text()
        .splitlines(),
    )
    crashInfoNeg = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_with_aux_and_abort_message.txt")
        .read_text()
        .splitlines(),
    )

    crashSignaturePos = crashInfoPos.createCrashSignature()
    crashSignatureNeg = crashInfoNeg.createCrashSignature()

    # Check that the first crash signature has ASan symptoms but
    # the second does not because it has a program abort message
    assert "/ERROR: AddressSanitizer" in str(crashSignaturePos)
    assert "/READ of size" in str(crashSignaturePos)
    assert "/ERROR: AddressSanitizer" not in str(crashSignatureNeg)
    assert "/READ of size" not in str(crashSignatureNeg)

    # Check matches appropriately
    assert crashSignaturePos.matches(crashInfoPos)
    assert crashSignaturePos.matches(crashInfoNeg)
    assert not crashSignatureNeg.matches(crashInfoPos)
    assert crashSignatureNeg.matches(crashInfoNeg)


def test_SignatureStackFramesNegativeSizeParamTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfoPos = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_asan_negative_size_param.txt")
        .read_text()
        .splitlines(),
    )

    testSig = crashInfoPos.createCrashSignature()

    assert "/ERROR: AddressSanitizer" in str(testSig)
    assert "negative-size-param" in str(testSig)
    assert isinstance(testSig.symptoms[1], StackFramesSymptom)


def test_SignatureAsanStackOverflowTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfoPos = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_asan_stack_overflow.txt")
        .read_text()
        .splitlines(),
    )

    testSig = crashInfoPos.createCrashSignature()

    # Check matches appropriately
    assert testSig.matches(crashInfoPos)


def test_SignatureAsanAccessViolationTest():
    config = ProgramConfiguration("test", "x86-64", "windows")
    crashInfoPos = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_asan_access_violation.txt")
        .read_text()
        .splitlines(),
    )

    testSig = crashInfoPos.createCrashSignature()

    assert "/ERROR: AddressSanitizer" not in str(testSig)
    assert "access-violation" not in str(testSig)
    assert isinstance(testSig.symptoms[0], StackFramesSymptom)


def test_SignatureStackSizeTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfoPos = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_asan_long.txt").read_text().splitlines(),
    )

    # The test signature uses > 15 which was previously interpreted as 0x15
    # while the test crash data has 16 frames.
    testSig = CrashSignature((FIXTURE_PATH / "sig_test_stack_size.json").read_text())
    assert testSig.matches(crashInfoPos)


def test_SignatureAsanFailedAllocTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfoPos = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_asan_failed_alloc.txt")
        .read_text()
        .splitlines(),
    )

    testSig = crashInfoPos.createCrashSignature()
    assert "/AddressSanitizer failed to allocate" in str(testSig)
    assert testSig.matches(crashInfoPos)
    assert isinstance(testSig.symptoms[1], StackFramesSymptom)


def test_SignatureGenerationTSanLeakTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "tsan-simple-leak-report.txt")
        .read_text()
        .splitlines(),
    )
    testSignature = crashInfo.createCrashSignature()

    assert testSignature.matches(crashInfo)

    found = False
    for symptom in testSignature.symptoms:
        if isinstance(symptom, OutputSymptom):
            assert symptom.src == "crashdata"
            assert symptom.output.value == "WARNING: ThreadSanitizer: thread leak"
            found = True
    assert found, "Expected correct OutputSymptom in signature"


def test_SignatureGenerationTSanRaceTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "tsan-simple-race-report.txt")
        .read_text()
        .splitlines(),
    )
    testSignature = crashInfo.createCrashSignature()

    print(testSignature)

    assert testSignature.matches(crashInfo)

    outputSymptoms = []

    for symptom in testSignature.symptoms:
        if isinstance(symptom, OutputSymptom):
            assert symptom.src == "crashdata"
            outputSymptoms.append(symptom)

    assert len(outputSymptoms) == 3

    for stringMatchVal in [
        "WARNING: ThreadSanitizer: data race",
        (
            "(Previous )?[Ww]rite of size 4 at 0x[0-9a-fA-F]+ by thread "
            "T[0-9]+( .+mutexes: .+)?:"
        ),
        (
            "(Previous )?[Rr]ead of size 4 at 0x[0-9a-fA-F]+ by main "
            "thread( .+mutexes: .+)?:"
        ),
    ]:
        found = False
        for symptom in outputSymptoms:
            if symptom.output.value == stringMatchVal:
                found = True
        assert found, f"Couldn't find OutputSymptom with value '{stringMatchVal}'"


def test_SignatureGenerationTSanRaceTestComplex1():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "tsan-report2.txt").read_text().splitlines(),
    )
    testSignature = crashInfo.createCrashSignature()

    print(testSignature)

    assert testSignature.matches(crashInfo)

    outputSymptoms = []

    for symptom in testSignature.symptoms:
        if isinstance(symptom, OutputSymptom):
            assert symptom.src == "crashdata"
            outputSymptoms.append(symptom)

    assert len(outputSymptoms) == 3

    for stringMatchVal in [
        "WARNING: ThreadSanitizer: data race",
        (
            "(Previous )?[Ww]rite of size 8 at 0x[0-9a-fA-F]+ by thread "
            "T[0-9]+( .+mutexes: .+)?:"
        ),
        (
            "(Previous )?[Ww]rite of size 8 at 0x[0-9a-fA-F]+ by thread "
            "T[0-9]+( .+mutexes: .+)?:"
        ),
    ]:
        found = False
        for symptom in outputSymptoms:
            if symptom.output.value == stringMatchVal:
                found = True
        assert found, f"Couldn't find OutputSymptom with value '{stringMatchVal}'"


def test_SignatureGenerationTSanRaceTestAtomic():
    config = ProgramConfiguration("test", "x86-64", "linux")
    for fn in ["tsan-report-atomic.txt", "tsan-report-atomic-swapped.txt"]:
        crashInfo = CrashInfo.fromRawCrashData(
            [], [], config, auxCrashData=(FIXTURE_PATH / fn).read_text().splitlines()
        )

        assert crashInfo.backtrace[0] == "pthread_mutex_destroy"
        assert crashInfo.createShortSignature() == (
            "ThreadSanitizer: data race [@ pthread_mutex_destroy] vs. "
            "[@ pthread_mutex_unlock]"
        )

        testSignature = crashInfo.createCrashSignature()

        assert testSignature.matches(crashInfo)

        outputSymptoms = []

        for symptom in testSignature.symptoms:
            if isinstance(symptom, OutputSymptom):
                assert symptom.src == "crashdata"
                outputSymptoms.append(symptom)

        assert len(outputSymptoms) == 3

        for stringMatchVal in [
            "WARNING: ThreadSanitizer: data race",
            (
                "(Previous )?[Aa]tomic [Rr]ead of size 1 at 0x[0-9a-fA-F]+ "
                "by thread T[0-9]+( .+mutexes: .+)?:"
            ),
            (
                "(Previous )?[Ww]rite of size 1 at 0x[0-9a-fA-F]+ "
                "by main thread( .+mutexes: .+)?:"
            ),
        ]:
            found = False
            for symptom in outputSymptoms:
                if symptom.output.value == stringMatchVal:
                    found = True
            assert found, f"Couldn't find OutputSymptom with value '{stringMatchVal}'"


def test_SignatureMatchWithUnicode():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        ["(Â«f => (generator.throw(f))Â», Â«undefinedÂ»)"], [], config
    )
    testSignature = CrashSignature(
        '{"symptoms": [{"src": "stdout", "type": "output", "value": "x"}]}'
    )
    assert not testSignature.matches(crashInfo)


def test_SignatureMatchAssertionSlashes():
    # test that a forward slash assertion signature matches a backwards slash crash, but
    # only on windows
    cfg_linux = ProgramConfiguration("test", "x86-64", "linux")
    cfg_windows = ProgramConfiguration("test", "x86-64", "windows")

    fs_lines = (
        (FIXTURE_PATH / "trace_assertion_path_fwd_slash.txt").read_text().splitlines()
    )
    bs_lines = (
        (FIXTURE_PATH / "trace_assertion_path_bwd_slash.txt").read_text().splitlines()
    )

    # native paths on linux use forward slash
    fs_linux = CrashInfo.fromRawCrashData([], [], cfg_linux, auxCrashData=fs_lines)
    # backward slash path on linux -- this is invalid and should never happen
    bs_linux = CrashInfo.fromRawCrashData([], [], cfg_linux, auxCrashData=bs_lines)
    # forward slashes on windows are valid, and this does happen
    fs_windows = CrashInfo.fromRawCrashData([], [], cfg_windows, auxCrashData=fs_lines)
    # native paths on windows use backslash
    bs_windows = CrashInfo.fromRawCrashData([], [], cfg_windows, auxCrashData=bs_lines)

    # test that signature generated from linux assertion matches both
    linux_sig = fs_linux.createCrashSignature()
    assert linux_sig.matches(fs_linux)
    assert not linux_sig.matches(bs_linux)  # this is invalid and should not match
    assert linux_sig.matches(fs_windows)
    assert linux_sig.matches(bs_windows)

    # test that signature generated from windows assertion matches both
    windows_sig = bs_windows.createCrashSignature()
    assert windows_sig.matches(fs_linux)
    assert not windows_sig.matches(bs_linux)  # this is invalid and should not match
    assert windows_sig.matches(fs_windows)
    assert windows_sig.matches(bs_windows)


def test_SignatureSanitizerSoftRssLimitHeapProfile():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_asan_soft_rss_heap_report.txt").read_text().splitlines(),
    )

    testSig = crashInfo.createCrashSignature()

    assert len(testSig.symptoms) == 1
    assert isinstance(testSig.symptoms[0], StackFramesSymptom)


def test_SignatureSanitizerHardRssLimitHeapProfile():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_asan_hard_rss_heap_report.txt").read_text().splitlines(),
    )

    testSig = crashInfo.createCrashSignature()

    assert len(testSig.symptoms) == 2
    assert isinstance(testSig.symptoms[0], OutputSymptom)
    assert (
        testSig.symptoms[0].output.value == "AddressSanitizer: hard rss limit exhausted"
    )
    assert testSig.symptoms[0].output.isPCRE
    assert isinstance(testSig.symptoms[1], StackFramesSymptom)
