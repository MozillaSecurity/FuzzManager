"""
Created on Oct 9, 2014

@author: decoder
"""
import json
from pathlib import Path

from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures.Matchers import StringMatch
from FTB.Signatures.ReportInfo import ReportInfo
from FTB.Signatures.ReportSignature import ReportSignature
from FTB.Signatures.Symptom import OutputSymptom, StackFramesSymptom

FIXTURE_PATH = Path(__file__).parent / "fixtures"


def test_SignatureCreateTest():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_1.txt").read_text().splitlines(),
    )

    reportSig1 = reportInfo.createReportSignature(
        forceReportAddress=True, maxFrames=4, minimumSupportedVersion=10
    )
    reportSig2 = reportInfo.createReportSignature(
        forceReportAddress=False, maxFrames=3, minimumSupportedVersion=10
    )
    reportSig3 = reportInfo.createReportSignature(
        forceReportInstruction=True, maxFrames=2, minimumSupportedVersion=10
    )

    # Check that all generated signatures match their originating reportInfo
    assert reportSig1.matches(reportInfo)
    assert reportSig2.matches(reportInfo)
    assert reportSig3.matches(reportInfo)

    # Check that the generated signatures look as expected
    with (FIXTURE_PATH / "sig_test_1.json").open() as f:
        assert json.loads(str(reportSig1)) == json.load(f)
    with (FIXTURE_PATH / "sig_test_2.json").open() as f:
        assert json.loads(str(reportSig2)) == json.load(f)

    #  The third reportInfo misses 2 frames from the top 4 frames, so it will
    #  also include the report address, even though we did not request it.
    with (FIXTURE_PATH / "sig_test_3.json").open() as f:
        assert json.loads(str(reportSig3)) == json.load(f)


def test_SignatureTestCaseMatchTest():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_1.txt").read_text().splitlines(),
    )

    testSig3 = ReportSignature((FIXTURE_PATH / "sig_test_3.json").read_text())
    testSig4 = ReportSignature((FIXTURE_PATH / "sig_test_4.json").read_text())
    testSig5 = ReportSignature((FIXTURE_PATH / "sig_test_5.json").read_text())
    testSig6 = ReportSignature((FIXTURE_PATH / "sig_test_6.json").read_text())

    assert not testSig3.matchRequiresTest()
    assert testSig4.matchRequiresTest()
    assert testSig5.matchRequiresTest()

    # Must not match without testcase provided
    assert not testSig4.matches(reportInfo)
    assert not testSig5.matches(reportInfo)
    assert not testSig6.matches(reportInfo)

    # Attach testcase
    reportInfo.testcase = (FIXTURE_PATH / "testcase_1.js").read_text()

    # Must match with testcase provided
    assert testSig4.matches(reportInfo)
    assert testSig5.matches(reportInfo)

    # This one does not match at all
    assert not testSig6.matches(reportInfo)


def test_SignatureStackFramesTest():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_1.txt").read_text().splitlines(),
    )

    testSig1 = ReportSignature(
        (FIXTURE_PATH / "sig_test_stack_frames_1.json").read_text()
    )
    testSig2 = ReportSignature(
        (FIXTURE_PATH / "sig_test_stack_frames_2.json").read_text()
    )
    testSig3 = ReportSignature(
        (FIXTURE_PATH / "sig_test_stack_frames_3.json").read_text()
    )
    testSig4 = ReportSignature(
        (FIXTURE_PATH / "sig_test_stack_frames_4.json").read_text()
    )
    testSig5 = ReportSignature(
        (FIXTURE_PATH / "sig_test_stack_frames_5.json").read_text()
    )

    assert testSig1.matches(reportInfo)
    assert testSig2.matches(reportInfo)
    assert testSig3.matches(reportInfo)
    assert testSig4.matches(reportInfo)
    assert not testSig5.matches(reportInfo)


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

    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_1.txt").read_text().splitlines(),
    )

    testSig1 = ReportSignature(
        (FIXTURE_PATH / "sig_test_pcre_short_1.json").read_text()
    )
    testSig2 = ReportSignature(
        (FIXTURE_PATH / "sig_test_pcre_short_2.json").read_text()
    )

    assert testSig1.matches(reportInfo)
    assert not testSig2.matches(reportInfo)


def test_SignatureStackFramesWildcardTailTest():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_2.txt").read_text().splitlines(),
    )

    testSig = reportInfo.createReportSignature()

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
    reportInfoNeg = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_heap_with_report_address.txt")
        .read_text()
        .splitlines(),
    )
    reportInfoPos = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_heap_without_report_address.txt")
        .read_text()
        .splitlines(),
    )

    testSigEmptyReportAddress = ReportSignature(
        (FIXTURE_PATH / "sig_test_empty_report_address.json").read_text()
    )

    assert testSigEmptyReportAddress.matches(reportInfoPos)
    assert not testSigEmptyReportAddress.matches(reportInfoNeg)


def test_SignatureStackFramesAuxMessagesTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfoPos = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_with_aux_message.txt")
        .read_text()
        .splitlines(),
    )
    reportInfoNeg = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_with_aux_and_abort_message.txt")
        .read_text()
        .splitlines(),
    )

    reportSignaturePos = reportInfoPos.createReportSignature()
    reportSignatureNeg = reportInfoNeg.createReportSignature()

    # Check that the first report signature has ASan symptoms but
    # the second does not because it has a program abort message
    assert "/ERROR: AddressSanitizer" in str(reportSignaturePos)
    assert "/READ of size" in str(reportSignaturePos)
    assert "/ERROR: AddressSanitizer" not in str(reportSignatureNeg)
    assert "/READ of size" not in str(reportSignatureNeg)

    # Check matches appropriately
    assert reportSignaturePos.matches(reportInfoPos)
    assert reportSignaturePos.matches(reportInfoNeg)
    assert not reportSignatureNeg.matches(reportInfoPos)
    assert reportSignatureNeg.matches(reportInfoNeg)


def test_SignatureStackFramesNegativeSizeParamTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfoPos = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_asan_negative_size_param.txt")
        .read_text()
        .splitlines(),
    )

    testSig = reportInfoPos.createReportSignature()

    assert "/ERROR: AddressSanitizer" in str(testSig)
    assert "negative-size-param" in str(testSig)
    assert isinstance(testSig.symptoms[1], StackFramesSymptom)


def test_SignatureAsanStackOverflowTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfoPos = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_asan_stack_overflow.txt")
        .read_text()
        .splitlines(),
    )

    testSig = reportInfoPos.createReportSignature()

    # Check matches appropriately
    assert testSig.matches(reportInfoPos)


def test_SignatureAsanAccessViolationTest():
    config = ProgramConfiguration("test", "x86-64", "windows")
    reportInfoPos = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_asan_access_violation.txt")
        .read_text()
        .splitlines(),
    )

    testSig = reportInfoPos.createReportSignature()

    assert "/ERROR: AddressSanitizer" not in str(testSig)
    assert "access-violation" not in str(testSig)
    assert isinstance(testSig.symptoms[0], StackFramesSymptom)


def test_SignatureStackSizeTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfoPos = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_asan_long.txt").read_text().splitlines(),
    )

    # The test signature uses > 15 which was previously interpreted as 0x15
    # while the test report data has 16 frames.
    testSig = ReportSignature((FIXTURE_PATH / "sig_test_stack_size.json").read_text())
    assert testSig.matches(reportInfoPos)


def test_SignatureAsanFailedAllocTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfoPos = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_asan_failed_alloc.txt")
        .read_text()
        .splitlines(),
    )

    testSig = reportInfoPos.createReportSignature()
    assert "/AddressSanitizer failed to allocate" in str(testSig)
    assert testSig.matches(reportInfoPos)
    assert isinstance(testSig.symptoms[1], StackFramesSymptom)


def test_SignatureGenerationTSanLeakTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "tsan-simple-leak-report.txt")
        .read_text()
        .splitlines(),
    )
    testSignature = reportInfo.createReportSignature()

    assert testSignature.matches(reportInfo)

    found = False
    for symptom in testSignature.symptoms:
        if isinstance(symptom, OutputSymptom):
            assert symptom.src == "reportdata"
            assert symptom.output.value == "WARNING: ThreadSanitizer: thread leak"
            found = True
    assert found, "Expected correct OutputSymptom in signature"


def test_SignatureGenerationTSanRaceTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "tsan-simple-race-report.txt")
        .read_text()
        .splitlines(),
    )
    testSignature = reportInfo.createReportSignature()

    print(testSignature)

    assert testSignature.matches(reportInfo)

    outputSymptoms = []

    for symptom in testSignature.symptoms:
        if isinstance(symptom, OutputSymptom):
            assert symptom.src == "reportdata"
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
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "tsan-report2.txt").read_text().splitlines(),
    )
    testSignature = reportInfo.createReportSignature()

    print(testSignature)

    assert testSignature.matches(reportInfo)

    outputSymptoms = []

    for symptom in testSignature.symptoms:
        if isinstance(symptom, OutputSymptom):
            assert symptom.src == "reportdata"
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
        reportInfo = ReportInfo.fromRawReportData(
            [], [], config, auxReportData=(FIXTURE_PATH / fn).read_text().splitlines()
        )

        assert reportInfo.backtrace[0] == "pthread_mutex_destroy"
        assert reportInfo.createShortSignature() == (
            "ThreadSanitizer: data race [@ pthread_mutex_destroy] vs. "
            "[@ pthread_mutex_unlock]"
        )

        testSignature = reportInfo.createReportSignature()

        assert testSignature.matches(reportInfo)

        outputSymptoms = []

        for symptom in testSignature.symptoms:
            if isinstance(symptom, OutputSymptom):
                assert symptom.src == "reportdata"
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
    reportInfo = ReportInfo.fromRawReportData(
        ["(Â«f => (generator.throw(f))Â», Â«undefinedÂ»)"], [], config
    )
    testSignature = ReportSignature(
        '{"symptoms": [{"src": "stdout", "type": "output", "value": "x"}]}'
    )
    assert not testSignature.matches(reportInfo)


def test_SignatureMatchAssertionSlashes():
    # test that a forward slash assertion signature matches a backwards slash report,
    # but only on windows
    cfg_linux = ProgramConfiguration("test", "x86-64", "linux")
    cfg_windows = ProgramConfiguration("test", "x86-64", "windows")

    fs_lines = (
        (FIXTURE_PATH / "trace_assertion_path_fwd_slash.txt").read_text().splitlines()
    )
    bs_lines = (
        (FIXTURE_PATH / "trace_assertion_path_bwd_slash.txt").read_text().splitlines()
    )

    # native paths on linux use forward slash
    fs_linux = ReportInfo.fromRawReportData([], [], cfg_linux, auxReportData=fs_lines)
    # backward slash path on linux -- this is invalid and should never happen
    bs_linux = ReportInfo.fromRawReportData([], [], cfg_linux, auxReportData=bs_lines)
    # forward slashes on windows are valid, and this does happen
    fs_windows = ReportInfo.fromRawReportData(
        [], [], cfg_windows, auxReportData=fs_lines
    )
    # native paths on windows use backslash
    bs_windows = ReportInfo.fromRawReportData(
        [], [], cfg_windows, auxReportData=bs_lines
    )

    # test that signature generated from linux assertion matches both
    linux_sig = fs_linux.createReportSignature()
    assert linux_sig.matches(fs_linux)
    assert not linux_sig.matches(bs_linux)  # this is invalid and should not match
    assert linux_sig.matches(fs_windows)
    assert linux_sig.matches(bs_windows)

    # test that signature generated from windows assertion matches both
    windows_sig = bs_windows.createReportSignature()
    assert windows_sig.matches(fs_linux)
    assert not windows_sig.matches(bs_linux)  # this is invalid and should not match
    assert windows_sig.matches(fs_windows)
    assert windows_sig.matches(bs_windows)


def test_SignatureSanitizerSoftRssLimitHeapProfile():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_asan_soft_rss_heap_report.txt").read_text().splitlines(),
    )

    testSig = reportInfo.createReportSignature()

    assert len(testSig.symptoms) == 1
    assert isinstance(testSig.symptoms[0], StackFramesSymptom)


def test_SignatureSanitizerHardRssLimitHeapProfile():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_asan_hard_rss_heap_report.txt").read_text().splitlines(),
    )

    testSig = reportInfo.createReportSignature()

    assert len(testSig.symptoms) == 2
    assert isinstance(testSig.symptoms[0], OutputSymptom)
    assert (
        testSig.symptoms[0].output.value == "AddressSanitizer: hard rss limit exhausted"
    )
    assert testSig.symptoms[0].output.isPCRE
    assert isinstance(testSig.symptoms[1], StackFramesSymptom)
