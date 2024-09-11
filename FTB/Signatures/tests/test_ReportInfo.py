"""
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""
import json
from pathlib import Path

import pytest

from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures import RegisterHelper
from FTB.Signatures.ReportInfo import (
    AppleReportInfo,
    ASanReportInfo,
    CDBReportInfo,
    GDBReportInfo,
    MinidumpReportInfo,
    NoReportInfo,
    ReportInfo,
    RustReportInfo,
    int32,
    unicode_escape_result,
)
from FTB.Signatures.ReportSignature import ReportSignature

FIXTURE_PATH = Path(__file__).parent / "fixtures"


def test_ASanParserTestAccessViolation():
    config = ProgramConfiguration("test", "x86-64", "windows")

    reportInfo = ASanReportInfo(
        [],
        (FIXTURE_PATH / "trace_asan_access_violation.txt").read_text().splitlines(),
        config,
    )
    assert len(reportInfo.backtrace) == 3
    assert reportInfo.backtrace[0] == "nsCSSFrameConstructor::WipeContainingBlock"
    assert reportInfo.backtrace[1] == "nsCSSFrameConstructor::ContentAppended"
    assert reportInfo.backtrace[2] == "mozilla::RestyleManager::ProcessRestyledFrames"

    assert reportInfo.reportAddress == 0x50
    assert reportInfo.registers["pc"] == 0x7FFA9A30C9E7
    assert reportInfo.registers["sp"] == 0x00F9915F0940
    assert reportInfo.registers["bp"] == 0x00F9915F0A20


def test_ASanParserTestReport():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo = ASanReportInfo(
        [], (FIXTURE_PATH / "trace_asan_segv.txt").read_text().splitlines(), config
    )
    assert len(reportInfo.backtrace) == 9
    assert reportInfo.backtrace[0] == "js::AbstractFramePtr::asRematerializedFrame"
    assert reportInfo.backtrace[2] == "EvalInFrame"
    assert reportInfo.backtrace[3] == "js::CallJSNative"
    assert reportInfo.backtrace[6] == "js::jit::DoCallFallback"
    assert (
        reportInfo.backtrace[7]
        == "/usr/lib/x86_64-linux-gnu/dri/swrast_dri.so+0x67edd0"
    )
    assert reportInfo.backtrace[8] == "<missing>"

    assert reportInfo.reportAddress == 0x00000014
    assert reportInfo.registers["pc"] == 0x0810845F
    assert reportInfo.registers["sp"] == 0xFFC57860
    assert reportInfo.registers["bp"] == 0xFFC57F18


def test_ASanParserTestReportWithWarning():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo = ASanReportInfo(
        [],
        (FIXTURE_PATH / "trace_asan_segv_with_warning.txt").read_text().splitlines(),
        config,
    )
    assert len(reportInfo.backtrace) == 7
    assert reportInfo.backtrace[0] == "js::AbstractFramePtr::asRematerializedFrame"
    assert reportInfo.backtrace[2] == "EvalInFrame"
    assert reportInfo.backtrace[3] == "js::CallJSNative"

    assert reportInfo.reportAddress == 0x00000014
    assert reportInfo.registers["pc"] == 0x0810845F
    assert reportInfo.registers["sp"] == 0xFFC57860
    assert reportInfo.registers["bp"] == 0xFFC57F18


def test_ASanParserTestFailedAlloc():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ASanReportInfo(
        [],
        (FIXTURE_PATH / "trace_asan_failed_alloc.txt").read_text().splitlines(),
        config,
    )
    assert len(reportInfo.backtrace) == 12
    assert reportInfo.backtrace[0] == "__asan::AsanCheckFailed"
    assert reportInfo.backtrace[7] == "oc_state_frarray_init"

    assert reportInfo.reportAddress is None
    assert not reportInfo.registers

    assert (
        "AddressSanitizer failed to allocate 0x6003a000 (1610850304) bytes of "
        "LargeMmapAllocator (error code: 12) [@ __asan::AsanCheckFailed]"
    ) == reportInfo.createShortSignature()


def test_ASanParserTestAllocSize():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ASanReportInfo(
        [],
        (FIXTURE_PATH / "trace_asan_alloc_size.txt").read_text().splitlines(),
        config,
    )
    assert len(reportInfo.backtrace) == 1
    assert reportInfo.backtrace[0] == "malloc"

    assert reportInfo.reportAddress is None
    assert not reportInfo.registers

    assert (
        "AddressSanitizer: requested allocation size exceeds maximum"
        " supported size [@ malloc]"
    ) == reportInfo.createShortSignature()


def test_ASanParserTestHeapReport():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo = ASanReportInfo(
        [],
        (FIXTURE_PATH / "trace_asan_heap_report.txt").read_text().splitlines(),
        config,
    )
    assert len(reportInfo.backtrace) == 0

    assert reportInfo.reportAddress == 0x00000019
    assert reportInfo.registers["pc"] == 0xF718072E
    assert reportInfo.registers["sp"] == 0xFF87D130
    assert reportInfo.registers["bp"] == 0x000006A1

    assert reportInfo.createShortSignature() == "[@ ??]"


def test_ASanParserTestUAF():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ASanReportInfo(
        [], (FIXTURE_PATH / "trace_asan_uaf.txt").read_text().splitlines(), config
    )
    assert len(reportInfo.backtrace) == 23
    assert reportInfo.backtrace[0] == "void mozilla::PodCopy<char16_t>"
    assert reportInfo.backtrace[4] == "JSFunction::native"

    assert reportInfo.reportAddress == 0x7FD766C42800

    assert (
        "AddressSanitizer: heap-use-after-free [@ void mozilla::PodCopy<char16_t>] "
        "with READ of size 6143520"
    ) == reportInfo.createShortSignature()


def test_ASanParserTestInvalidFree():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ASanReportInfo(
        [],
        (FIXTURE_PATH / "trace_asan_invalid_free.txt").read_text().splitlines(),
        config,
    )
    assert len(reportInfo.backtrace) == 1
    assert reportInfo.backtrace[0] == "__interceptor_free"

    assert reportInfo.reportAddress == 0x62A00006C200

    assert (
        "AddressSanitizer: attempting free on address which was not malloc()-ed "
        "[@ __interceptor_free]"
    ) == reportInfo.createShortSignature()


def test_ASanParserTestOOM():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ASanReportInfo(
        [], (FIXTURE_PATH / "trace_asan_oom.txt").read_text().splitlines(), config
    )
    assert len(reportInfo.backtrace) == 2
    assert reportInfo.backtrace[0] == "operator new"
    assert reportInfo.backtrace[1] == (
        "std::vector<"
        "std::pair<unsigned short, llvm::LegalizeActions::LegalizeAction>, "
        "std::allocator<"
        "std::pair<unsigned short, llvm::LegalizeActions::LegalizeAction> "
        "> >::operator="
    )

    assert reportInfo.reportAddress is None

    assert (
        "AddressSanitizer: allocator is out of memory trying to allocate 0x24 bytes "
        "[@ operator new]"
    ) == reportInfo.createShortSignature()


def test_ASanParserTestDebugAssertion():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ASanReportInfo(
        [],
        (FIXTURE_PATH / "trace_asan_debug_assertion.txt").read_text().splitlines(),
        config,
    )
    assert len(reportInfo.backtrace) == 8
    assert reportInfo.backtrace[0] == "nsCycleCollector::CollectWhite"
    assert (
        reportInfo.backtrace[6]
        == "mozilla::DefaultDelete<ScopedXPCOMStartup>::operator()"
    )

    assert reportInfo.reportAddress == 0x0

    assert (
        "Assertion failure: false (An assert from the graphics logger), at "
        "/builds/slave/m-cen-l64-asan-d-0000000000000/build/src/gfx/2d/Logging.h:521"
    ) == reportInfo.createShortSignature()


@pytest.mark.parametrize(
    "stderr_path, report_data_path",
    [
        (None, "trace_asan_segv.txt"),
        ("trace_asan_uaf.txt", None),
        (None, "trace_asan_segv_with_warning.txt"),
        (None, "trace_tsan_report.txt"),
        (None, "trace_ubsan_generic_report.txt"),
    ],
)
def test_ASanDetectionTest(stderr_path, report_data_path):
    config = ProgramConfiguration("test", "x86", "linux")
    stderr = "" if stderr_path is None else (FIXTURE_PATH / stderr_path).read_text()
    report_data = (
        ""
        if report_data_path is None
        else (FIXTURE_PATH / report_data_path).read_text()
    )
    reportInfo = ReportInfo.fromRawReportData(
        [],
        stderr.splitlines(),
        config,
        auxReportData=report_data.splitlines(),
    )
    assert isinstance(reportInfo, ASanReportInfo)


def test_ASanParserTestParamOverlap():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ASanReportInfo(
        [],
        (FIXTURE_PATH / "trace_asan_memcpy_param_overlap.txt").read_text().splitlines(),
        config,
    )
    assert reportInfo.reportAddress is None
    assert len(reportInfo.backtrace) == 2
    assert reportInfo.backtrace[0] == "__asan_memcpy"
    assert reportInfo.backtrace[1] == "S32_Opaque_BlitRow32"
    assert reportInfo.createShortSignature() == (
        "AddressSanitizer: memcpy-param-overlap: memory ranges overlap "
        "[@ __asan_memcpy]"
    )

    reportInfo = ASanReportInfo(
        [],
        (FIXTURE_PATH / "trace_asan_strcat_param_overlap.txt").read_text().splitlines(),
        config,
    )
    assert reportInfo.reportAddress is None
    assert len(reportInfo.backtrace) == 1
    assert reportInfo.backtrace[0] == "__interceptor_strcat"
    assert reportInfo.createShortSignature() == (
        "AddressSanitizer: strcat-param-overlap: memory ranges overlap "
        "[@ __interceptor_strcat]"
    )


def test_ASanParserTestMultiTrace():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ASanReportInfo(
        [], (FIXTURE_PATH / "trace_asan_multiple.txt").read_text().splitlines(), config
    )
    assert reportInfo.reportAddress == 0x7F637B59CFFC
    assert len(reportInfo.backtrace) == 4
    assert reportInfo.backtrace[0] == "mozilla::ipc::Shmem::OpenExisting"
    assert reportInfo.backtrace[3] == "CreateThread"
    assert "[@ mozilla::ipc::Shmem::OpenExisting]" == reportInfo.createShortSignature()


def test_ASanParserTestTruncatedTrace():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ASanReportInfo(
        [], (FIXTURE_PATH / "trace_asan_truncated.txt").read_text().splitlines(), config
    )

    # Make sure we parsed it as a report, but without a backtrace
    assert len(reportInfo.backtrace) == 0
    assert reportInfo.reportAddress == 0x0

    # Confirm that generating a report signature will fail
    reportSig = reportInfo.createReportSignature()
    assert reportSig is None
    assert "Insufficient data" in reportInfo.failureReason


def test_ASanParserTestClang14():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ASanReportInfo(
        [], (FIXTURE_PATH / "trace_asan_clang14.txt").read_text().splitlines(), config
    )
    assert reportInfo.reportAddress == 0x03E800004610
    assert reportInfo.backtrace == [
        "raise",
        "abort",
        "llvm::report_fatal_error",
        "llvm::report_fatal_error",
    ]
    assert "[@ raise]" == reportInfo.createShortSignature()


def test_GDBParserTestReport():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo = GDBReportInfo(
        [], (FIXTURE_PATH / "trace_gdb_sample_1.txt").read_text().splitlines(), config
    )
    assert len(reportInfo.backtrace) == 8
    assert reportInfo.backtrace[0] == "internalAppend<js::ion::MDefinition*>"
    assert reportInfo.backtrace[2] == "js::ion::MPhi::addInput"
    assert reportInfo.backtrace[6] == "processCfgStack"

    assert reportInfo.registers["eax"] == 0x0
    assert reportInfo.registers["ebx"] == 0x8962FF4
    assert reportInfo.registers["eip"] == 0x818BC33


def test_GDBParserTestReportAddress():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo1 = GDBReportInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_report_addr_1.txt").read_text().splitlines(),
        config,
    )
    reportInfo2 = GDBReportInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_report_addr_2.txt").read_text().splitlines(),
        config,
    )
    reportInfo3 = GDBReportInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_report_addr_3.txt").read_text().splitlines(),
        config,
    )
    reportInfo4 = GDBReportInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_report_addr_4.txt").read_text().splitlines(),
        config,
    )
    reportInfo5 = GDBReportInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_report_addr_5.txt").read_text().splitlines(),
        config,
    )

    assert reportInfo1.reportAddress == 0x1
    assert reportInfo2.reportAddress == 0x0
    assert reportInfo3.reportAddress == 0xFFFFFFFFFFFFFFA0
    assert reportInfo4.reportAddress == 0x3EF29D14
    assert reportInfo5.reportAddress == 0x87AFA014


def test_GDBParserTestReportAddressSimple():
    registerMap64 = {}
    registerMap64["rax"] = 0x0
    registerMap64["rbx"] = -1
    registerMap64["rsi"] = 0xDE6E5
    registerMap64["rdi"] = 0x7FFFF6543238

    registerMap32 = {}
    registerMap32["eax"] = 0x0
    registerMap32["ebx"] = -1
    registerMap32["ecx"] = 0xF75FFFB8

    # Simple tests
    assert (
        GDBReportInfo.calculateReportAddress("mov    %rbx,0x10(%rax)", registerMap64)
        == 0x10
    )
    assert (
        GDBReportInfo.calculateReportAddress("mov    %ebx,0x10(%eax)", registerMap32)
        == 0x10
    )

    # Overflow tests
    assert (
        GDBReportInfo.calculateReportAddress("mov    %rax,0x10(%rbx)", registerMap64)
        == 0xF
    )
    assert (
        GDBReportInfo.calculateReportAddress("mov    %eax,0x10(%ebx)", registerMap32)
        == 0xF
    )

    assert (
        GDBReportInfo.calculateReportAddress("mov    %rbx,-0x10(%rax)", registerMap64)
        == -16
    )
    assert (
        GDBReportInfo.calculateReportAddress("mov    %ebx,-0x10(%eax)", registerMap32)
        == -16
    )

    # Scalar test
    assert (
        GDBReportInfo.calculateReportAddress("movl   $0x7b,0x0", registerMap32) == 0x0
    )

    # Real world examples
    # Note: The report address here can also be 0xf7600000 because the double quadword
    # move can fail on the second 8 bytes if the source address is not 16-byte aligned
    assert GDBReportInfo.calculateReportAddress(
        "movdqu 0x40(%ecx),%xmm4", registerMap32
    ) == int32(0xF75FFFF8)

    # Again, this is an unaligned access and the report can be at 0x7ffff6700000
    # or 0x7ffff6700000 - 4
    assert (
        GDBReportInfo.calculateReportAddress(
            "mov    -0x4(%rdi,%rsi,2),%eax", registerMap64
        )
        == 0x7FFFF66FFFFE
    )


def test_GDBParserTestRegression1():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo1 = GDBReportInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_regression_1.txt").read_text().splitlines(),
        config,
    )

    assert (
        reportInfo1.backtrace[0] == "js::ScriptedIndirectProxyHandler::defineProperty"
    )
    assert reportInfo1.backtrace[1] == "js::SetPropertyIgnoringNamedGetter"


def test_GDBParserTestReportAddressRegression2():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo2 = GDBReportInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_regression_2.txt").read_text().splitlines(),
        config,
    )

    assert reportInfo2.reportAddress == 0xFFFD579C


def test_GDBParserTestReportAddressRegression3():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo3 = GDBReportInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_regression_3.txt").read_text().splitlines(),
        config,
    )

    assert reportInfo3.reportAddress == 0x7FFFFFFFFFFF


def test_GDBParserTestReportAddressRegression4():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo4 = GDBReportInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_regression_4.txt").read_text().splitlines(),
        config,
    )

    assert reportInfo4.reportAddress == 0x0


def test_GDBParserTestReportAddressRegression5():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo5 = GDBReportInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_regression_5.txt").read_text().splitlines(),
        config,
    )

    assert reportInfo5.reportAddress == 0xFFFD573C


def test_GDBParserTestReportAddressRegression6():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo6 = GDBReportInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_regression_6.txt").read_text().splitlines(),
        config,
    )

    assert reportInfo6.reportAddress == 0xF7673132


def test_GDBParserTestReportAddressRegression7():
    config = ProgramConfiguration("test", "x86", "linux")

    # This used to fail because ReportInfo.fromRawReportData fails to detect a GDB trace
    reportInfo7 = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_7.txt").read_text().splitlines(),
    )

    assert reportInfo7.backtrace[1] == "js::ScopeIter::settle"


def test_GDBParserTestReportAddressRegression8():
    config = ProgramConfiguration("test", "x86", "linux")

    # This used to fail because ReportInfo.fromRawReportData fails to detect a GDB trace
    reportInfo8 = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_8.txt").read_text().splitlines(),
    )

    assert (
        reportInfo8.backtrace[2]
        == "js::jit::AutoLockSimulatorCache::AutoLockSimulatorCache"
    )
    assert reportInfo8.backtrace[3] == "<signal handler called>"
    assert reportInfo8.backtrace[4] == "??"
    assert reportInfo8.backtrace[5] == "js::jit::CheckICacheLocked"


def test_GDBParserTestReportAddressRegression9():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo9 = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_9.txt").read_text().splitlines(),
    )
    assert reportInfo9.reportInstruction == "call   0x8120ca0"


def test_GDBParserTestReportAddressRegression10():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo10 = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_10.txt").read_text().splitlines(),
    )
    assert reportInfo10.reportInstruction == "(bad)"
    assert reportInfo10.reportAddress == 0x7FF7F20C1F81


def test_GDBParserTestReportAddressRegression11():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo11 = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_11.txt").read_text().splitlines(),
    )
    assert reportInfo11.reportInstruction == "callq  *0xa8(%rax)"
    assert reportInfo11.reportAddress == 0x7FF7F2091032


def test_GDBParserTestReportAddressRegression12():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo12 = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_12.txt").read_text().splitlines(),
    )
    assert reportInfo12.backtrace[0] == "js::SavedStacks::insertFrames"
    assert reportInfo12.backtrace[1] == "js::SavedStacks::saveCurrentStack"
    assert reportInfo12.backtrace[2] == "JS::CaptureCurrentStack"
    assert reportInfo12.backtrace[3] == "CaptureStack"


def test_GDBParserTestReportAddressRegression13():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo13 = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_13.txt").read_text().splitlines(),
    )
    assert reportInfo13.backtrace[0] == "JSScript::global"
    assert reportInfo13.backtrace[1] == "js::AbstractFramePtr::global"
    assert reportInfo13.backtrace[5] == "js::jit::HandleException"
    assert reportInfo13.backtrace[6] == "??"

    assert reportInfo13.reportInstruction == "pushl  0x10(%eax)"
    assert reportInfo13.reportAddress == 0xE5E5E5F5


def test_ReportSignatureOutputTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportSignature1 = '{ "symptoms" : [ { "type" : "output", "value" : "test" } ] }'
    reportSignature1Neg = (
        '{ "symptoms" : [ { "type" : "output", "src" : "stderr", "value" : "test" } ] }'
    )
    reportSignature2 = (
        '{ "symptoms" : [ { "type" : "output", "src" : "stderr", "value" : { '
        '"value" : "^fest$", "matchType" : "pcre" } } ] }'
    )

    outputSignature1 = ReportSignature(reportSignature1)
    outputSignature1Neg = ReportSignature(reportSignature1Neg)
    outputSignature2 = ReportSignature(reportSignature2)

    gdbOutput = []
    stdout = []
    stderr = []

    stdout.append("Foo")
    stdout.append("Bartester")
    stdout.append("Baz")
    stderr.append("hackfest")

    reportInfo = ReportInfo.fromRawReportData(
        stdout, stderr, config, auxReportData=gdbOutput
    )

    assert isinstance(reportInfo, NoReportInfo)

    # Ensure we match on stdout/err if nothing is specified
    assert outputSignature1.matches(reportInfo)

    # Don't match stdout if stderr is specified
    assert not outputSignature1Neg.matches(reportInfo)

    # Check that we're really using PCRE
    assert not outputSignature2.matches(reportInfo)

    # Add something the PCRE should match, then retry
    stderr.append("fest")
    reportInfo = ReportInfo.fromRawReportData(
        stdout, stderr, config, auxReportData=gdbOutput
    )
    assert outputSignature2.matches(reportInfo)


def test_ReportSignatureAddressTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportSignature1 = (
        '{ "symptoms" : [ { "type" : "reportAddress", "address" : "< 0x1000" } ] }'
    )
    reportSignature1Neg = (
        '{ "symptoms" : [ { "type" : "reportAddress", "address" : "0x1000" } ] }'
    )
    addressSig1 = ReportSignature(reportSignature1)
    addressSig1Neg = ReportSignature(reportSignature1Neg)

    reportInfo1 = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_gdb_sample_1.txt")
        .read_text()
        .splitlines(),
    )
    reportInfo3 = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_gdb_sample_3.txt")
        .read_text()
        .splitlines(),
    )

    assert isinstance(reportInfo1, GDBReportInfo)

    assert addressSig1.matches(reportInfo1)
    assert not addressSig1Neg.matches(reportInfo1)

    # For reportInfo3, we don't have a report address. Ensure we don't match
    assert not addressSig1.matches(reportInfo3)
    assert not addressSig1Neg.matches(reportInfo3)


def test_ReportSignatureRegisterTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportSignature1 = {"symptoms": [{"type": "instruction", "registerNames": ["r14"]}]}
    reportSignature1Neg = {
        "symptoms": [{"type": "instruction", "registerNames": ["r14", "rax"]}]
    }
    reportSignature2 = {"symptoms": [{"type": "instruction", "instructionName": "mov"}]}
    reportSignature2Neg = {
        "symptoms": [{"type": "instruction", "instructionName": "cmp"}]
    }
    reportSignature3 = {
        "symptoms": [
            {
                "type": "instruction",
                "instructionName": "mov",
                "registerNames": ["r14", "rbx"],
            }
        ]
    }
    reportSignature3Neg = {
        "symptoms": [
            {
                "type": "instruction",
                "instructionName": "mov",
                "registerNames": ["r14", "rax"],
            }
        ]
    }

    instructionSig1 = ReportSignature(json.dumps(reportSignature1))
    instructionSig1Neg = ReportSignature(json.dumps(reportSignature1Neg))

    instructionSig2 = ReportSignature(json.dumps(reportSignature2))
    instructionSig2Neg = ReportSignature(json.dumps(reportSignature2Neg))

    instructionSig3 = ReportSignature(json.dumps(reportSignature3))
    instructionSig3Neg = ReportSignature(json.dumps(reportSignature3Neg))

    reportInfo2 = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_gdb_sample_2.txt")
        .read_text()
        .splitlines(),
    )
    reportInfo3 = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_gdb_sample_3.txt")
        .read_text()
        .splitlines(),
    )

    assert isinstance(reportInfo2, GDBReportInfo)
    assert isinstance(reportInfo3, GDBReportInfo)

    assert instructionSig1.matches(reportInfo2)
    assert not instructionSig1Neg.matches(reportInfo2)

    assert instructionSig2.matches(reportInfo2)
    assert not instructionSig2Neg.matches(reportInfo2)

    assert instructionSig3.matches(reportInfo2)
    assert not instructionSig3Neg.matches(reportInfo2)

    # Report info3 doesn't have register information, ensure we don't match any
    assert not instructionSig1.matches(reportInfo3)
    assert not instructionSig2.matches(reportInfo3)
    assert not instructionSig3.matches(reportInfo3)


def test_ReportSignatureStackFrameTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportSignature1 = {
        "symptoms": [{"type": "stackFrame", "functionName": "internalAppend"}]
    }
    reportSignature1Neg = {
        "symptoms": [{"type": "stackFrame", "functionName": "foobar"}]
    }

    reportSignature2 = {
        "symptoms": [
            {
                "type": "stackFrame",
                "functionName": "js::ion::MBasicBlock::setBackedge",
                "frameNumber": "<= 4",
            }
        ]
    }
    reportSignature2Neg = {
        "symptoms": [
            {
                "type": "stackFrame",
                "functionName": "js::ion::MBasicBlock::setBackedge",
                "frameNumber": "> 4",
            }
        ]
    }

    stackFrameSig1 = ReportSignature(json.dumps(reportSignature1))
    stackFrameSig1Neg = ReportSignature(json.dumps(reportSignature1Neg))

    stackFrameSig2 = ReportSignature(json.dumps(reportSignature2))
    stackFrameSig2Neg = ReportSignature(json.dumps(reportSignature2Neg))

    reportInfo1 = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_gdb_sample_1.txt")
        .read_text()
        .splitlines(),
    )

    assert isinstance(reportInfo1, GDBReportInfo)

    assert stackFrameSig1.matches(reportInfo1)
    assert not stackFrameSig1Neg.matches(reportInfo1)

    assert stackFrameSig2.matches(reportInfo1)
    assert not stackFrameSig2Neg.matches(reportInfo1)


def test_ReportSignatureStackSizeTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportSignature1 = '{ "symptoms" : [ { "type" : "stackSize", "size" : 8 } ] }'
    reportSignature1Neg = '{ "symptoms" : [ { "type" : "stackSize", "size" : 9 } ] }'

    reportSignature2 = '{ "symptoms" : [ { "type" : "stackSize", "size" : "< 10" } ] }'
    reportSignature2Neg = (
        '{ "symptoms" : [ { "type" : "stackSize", "size" : "> 10" } ] }'
    )

    stackSizeSig1 = ReportSignature(reportSignature1)
    stackSizeSig1Neg = ReportSignature(reportSignature1Neg)

    stackSizeSig2 = ReportSignature(reportSignature2)
    stackSizeSig2Neg = ReportSignature(reportSignature2Neg)

    reportInfo1 = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        auxReportData=(FIXTURE_PATH / "trace_gdb_sample_1.txt")
        .read_text()
        .splitlines(),
    )

    assert isinstance(reportInfo1, GDBReportInfo)

    assert stackSizeSig1.matches(reportInfo1)
    assert not stackSizeSig1Neg.matches(reportInfo1)

    assert stackSizeSig2.matches(reportInfo1)
    assert not stackSizeSig2Neg.matches(reportInfo1)


def test_RegisterHelperValueTest():
    registerMap = {"rax": 0xFFFFFFFFFFFFFE00, "rbx": 0x7FFFF79A7640}

    assert RegisterHelper.getRegisterValue("rax", registerMap) == 0xFFFFFFFFFFFFFE00
    assert RegisterHelper.getRegisterValue("eax", registerMap) == 0xFFFFFE00
    assert RegisterHelper.getRegisterValue("ax", registerMap) == 0xFE00
    assert RegisterHelper.getRegisterValue("ah", registerMap) == 0xFE
    assert RegisterHelper.getRegisterValue("al", registerMap) == 0x0

    assert RegisterHelper.getRegisterValue("rbx", registerMap) == 0x7FFFF79A7640
    assert RegisterHelper.getRegisterValue("ebx", registerMap) == 0xF79A7640
    assert RegisterHelper.getRegisterValue("bx", registerMap) == 0x7640
    assert RegisterHelper.getRegisterValue("bh", registerMap) == 0x76
    assert RegisterHelper.getRegisterValue("bl", registerMap) == 0x40


def test_MinidumpParserTestReport():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo = MinidumpReportInfo(
        [], (FIXTURE_PATH / "minidump-example.txt").read_text().splitlines(), config
    )

    assert len(reportInfo.backtrace) == 44
    assert reportInfo.backtrace[0] == "libc-2.15.so+0xe6b03"
    assert reportInfo.backtrace[5] == "libglib-2.0.so.0.3200.1+0x48123"
    assert reportInfo.backtrace[6] == "nsAppShell::ProcessNextNativeEvent"
    assert reportInfo.backtrace[7] == "nsBaseAppShell::DoProcessNextNativeEvent"

    assert reportInfo.reportAddress == 0x3E800006ACB


def test_MinidumpSelectorTest():
    config = ProgramConfiguration("test", "x86", "linux")

    reportData = (FIXTURE_PATH / "minidump-example.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x3E800006ACB


def test_MinidumpFromMacOSTest():
    config = ProgramConfiguration("test", "x86-64", "macosx")

    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_minidump_macos.txt").read_text().splitlines(),
    )
    assert len(reportInfo.backtrace) == 4
    assert reportInfo.backtrace[0] == "nsIFrame::UpdateOverflow"
    assert reportInfo.backtrace[1] == "mozilla::OverflowChangedTracker::Flush"
    assert (
        reportInfo.backtrace[2] == "mozilla::RestyleManager::DoProcessPendingRestyles"
    )
    assert reportInfo.backtrace[3] == "mozilla::PresShell::DoFlushPendingNotifications"
    assert reportInfo.reportAddress == 0


def test_AppleParserTestReport():
    config = ProgramConfiguration("test", "x86-64", "macosx")

    reportInfo = AppleReportInfo(
        [],
        [],
        config,
        (FIXTURE_PATH / "apple-report-report-example.txt").read_text().splitlines(),
    )

    assert len(reportInfo.backtrace) == 9
    assert reportInfo.backtrace[0] == "js::jit::MacroAssembler::Pop"
    assert (
        reportInfo.backtrace[1]
        == "js::jit::ICGetPropCallNativeCompiler::generateStubCode"
    )
    assert reportInfo.backtrace[2] == "js::jit::ICStubCompiler::getStubCode"
    assert reportInfo.backtrace[3] == "js::jit::ICGetPropCallNativeCompiler::getStub"
    assert reportInfo.backtrace[4] == "js::jit::DoGetPropFallback"
    assert reportInfo.backtrace[5] == "??"
    assert reportInfo.backtrace[6] == "__cxa_finalize_ranges"
    assert reportInfo.backtrace[7] == "??"
    assert (
        reportInfo.backtrace[8]
        == "-[NSApplication _nextEventMatchingEventMask:untilDate:inMode:dequeue:]"
    )

    assert reportInfo.reportAddress == 0x00007FFF5F3FFF98


def test_AppleSelectorTest():
    config = ProgramConfiguration("test", "x86-64", "macosx")

    reportData = (
        (FIXTURE_PATH / "apple-report-report-example.txt").read_text().splitlines()
    )

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x00007FFF5F3FFF98


def test_AppleLionParserTestReport():
    config = ProgramConfiguration("test", "x86-64", "macosx64")

    reportInfo = AppleReportInfo(
        [],
        [],
        config,
        (FIXTURE_PATH / "apple-10-7-report-report-example.txt")
        .read_text()
        .splitlines(),
    )

    assert len(reportInfo.backtrace) == 13
    assert reportInfo.backtrace[0] == "js::jit::LIRGenerator::visitNearbyInt"
    assert reportInfo.backtrace[1] == "js::jit::LIRGenerator::visitInstruction"
    assert reportInfo.backtrace[2] == "js::jit::LIRGenerator::visitBlock"
    assert reportInfo.backtrace[3] == "js::jit::LIRGenerator::generate"
    assert reportInfo.backtrace[4] == "js::jit::GenerateLIR"
    assert reportInfo.backtrace[5] == "js::jit::CompileBackEnd"
    assert reportInfo.backtrace[6] == (
        "_ZN2js3jitL7CompileEP9JSContextN2JS6Handle"
        "IP8JSScriptEEPNS0_13BaselineFrameEPhb"
    )
    assert reportInfo.backtrace[7] == "js::jit::IonCompileScriptForBaseline"
    assert reportInfo.backtrace[8] == "??"
    assert reportInfo.backtrace[9] == "??"
    assert reportInfo.backtrace[10] == "??"
    assert reportInfo.backtrace[11] == "??"
    assert (
        reportInfo.backtrace[12]
        == "_ZL13EnterBaselineP9JSContextRN2js3jit12EnterJitDataE"
    )

    assert reportInfo.reportAddress == 0x0000000000000000


def test_AppleLionSelectorTest():
    config = ProgramConfiguration("test", "x86-64", "macosx64")

    reportData = (
        (FIXTURE_PATH / "apple-10-7-report-report-example.txt").read_text().splitlines()
    )

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x0000000000000000


# Test 1a is for Win7 with 32-bit js debug deterministic shell hitting the assertion
# failure:
#     js_dbg_32_dm_windows_62f79d676e0e!js::GetBytecodeLength
#     01814577 cc              int     3
def test_CDBParserTestReport1a():
    config = ProgramConfiguration("test", "x86", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-1a-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 13
    assert reportInfo.backtrace[0] == "js::GetBytecodeLength"
    assert reportInfo.backtrace[1] == "js::coverage::LCovSource::writeScript"
    assert (
        reportInfo.backtrace[2]
        == "js::coverage::LCovCompartment::collectCodeCoverageInfo"
    )
    assert reportInfo.backtrace[3] == "GenerateLcovInfo"
    assert reportInfo.backtrace[4] == "js::GetCodeCoverageSummary"
    assert reportInfo.backtrace[5] == "GetLcovInfo"
    assert reportInfo.backtrace[6] == "js::CallJSNative"
    assert reportInfo.backtrace[7] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[8] == "InternalCall"
    assert reportInfo.backtrace[9] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[10] == "??"
    assert reportInfo.backtrace[11] == "EnterIon"
    assert reportInfo.backtrace[12] == "??"

    assert reportInfo.reportInstruction == "int 3"
    assert reportInfo.registers["eax"] == 0x00000000
    assert reportInfo.registers["ebx"] == 0x00000001
    assert reportInfo.registers["ecx"] == 0x6A24705D
    assert reportInfo.registers["edx"] == 0x0034D9D4
    assert reportInfo.registers["esi"] == 0x0925B3EC
    assert reportInfo.registers["edi"] == 0x0925B3D1
    assert reportInfo.registers["eip"] == 0x01814577
    assert reportInfo.registers["esp"] == 0x0034EF5C
    assert reportInfo.registers["ebp"] == 0x0034EF5C

    assert reportInfo.reportAddress == 0x01814577


def test_CDBSelectorTest1a():
    config = ProgramConfiguration("test", "x86", "windows")

    reportData = (FIXTURE_PATH / "cdb-1a-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x01814577


# Test 1b is for Win10 with 32-bit js debug deterministic shell hitting the assertion
# failure:
#     js_dbg_32_dm_windows_62f79d676e0e!js::GetBytecodeLength+47
#     01344577 cc              int     3
def test_CDBParserTestReport1b():
    config = ProgramConfiguration("test", "x86", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-1b-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 13
    assert reportInfo.backtrace[0] == "js::GetBytecodeLength"
    assert reportInfo.backtrace[1] == "js::coverage::LCovSource::writeScript"
    assert (
        reportInfo.backtrace[2]
        == "js::coverage::LCovCompartment::collectCodeCoverageInfo"
    )
    assert reportInfo.backtrace[3] == "GenerateLcovInfo"
    assert reportInfo.backtrace[4] == "js::GetCodeCoverageSummary"
    assert reportInfo.backtrace[5] == "GetLcovInfo"
    assert reportInfo.backtrace[6] == "js::CallJSNative"
    assert reportInfo.backtrace[7] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[8] == "InternalCall"
    assert reportInfo.backtrace[9] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[10] == "??"
    assert reportInfo.backtrace[11] == "EnterIon"
    assert reportInfo.backtrace[12] == "??"

    assert reportInfo.reportInstruction == "int 3"
    assert reportInfo.registers["eax"] == 0x00000000
    assert reportInfo.registers["ebx"] == 0x00000001
    assert reportInfo.registers["ecx"] == 0x765E06EF
    assert reportInfo.registers["edx"] == 0x00000060
    assert reportInfo.registers["esi"] == 0x039604EC
    assert reportInfo.registers["edi"] == 0x039604D1
    assert reportInfo.registers["eip"] == 0x01344577
    assert reportInfo.registers["esp"] == 0x02B2EE1C
    assert reportInfo.registers["ebp"] == 0x02B2EE1C

    assert reportInfo.reportAddress == 0x01344577


def test_CDBSelectorTest1b():
    config = ProgramConfiguration("test", "x86", "windows")

    reportData = (FIXTURE_PATH / "cdb-1b-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x01344577


# Test 2a is for Win7 with 64-bit js debug deterministic shell hitting the assertion
# failure:
#     js_dbg_64_dm_windows_62f79d676e0e!js::GetBytecodeLength
#     00000001`40144e62 cc              int     3
def test_CDBParserTestReport2a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-2a-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 25
    assert reportInfo.backtrace[0] == "js::GetBytecodeLength"
    assert reportInfo.backtrace[1] == "js::coverage::LCovSource::writeScript"
    assert (
        reportInfo.backtrace[2]
        == "js::coverage::LCovCompartment::collectCodeCoverageInfo"
    )
    assert reportInfo.backtrace[3] == "GenerateLcovInfo"
    assert reportInfo.backtrace[4] == "js::GetCodeCoverageSummary"
    assert reportInfo.backtrace[5] == "GetLcovInfo"
    assert reportInfo.backtrace[6] == "js::CallJSNative"
    assert reportInfo.backtrace[7] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[8] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[9] == "??"
    assert reportInfo.backtrace[10] == "??"
    assert reportInfo.backtrace[11] == "??"
    assert reportInfo.backtrace[12] == "??"
    assert reportInfo.backtrace[13] == "??"
    assert reportInfo.backtrace[14] == "??"
    assert reportInfo.backtrace[15] == "??"
    assert reportInfo.backtrace[16] == "??"
    assert reportInfo.backtrace[17] == "??"
    assert reportInfo.backtrace[18] == "??"
    assert reportInfo.backtrace[19] == "??"
    assert reportInfo.backtrace[20] == "??"
    assert reportInfo.backtrace[21] == "??"
    assert reportInfo.backtrace[22] == "??"
    assert reportInfo.backtrace[23] == "??"
    assert reportInfo.backtrace[24] == "??"

    assert reportInfo.reportInstruction == "int 3"
    assert reportInfo.registers["rax"] == 0x0000000000000000
    assert reportInfo.registers["rbx"] == 0x0000000006C139AC
    assert reportInfo.registers["rcx"] == 0x000007FEF38241F0
    assert reportInfo.registers["rdx"] == 0x000007FEF38255F0
    assert reportInfo.registers["rsi"] == 0x0000000006C1399E
    assert reportInfo.registers["rdi"] == 0x0000000006CF2101
    assert reportInfo.registers["rip"] == 0x0000000140144E62
    assert reportInfo.registers["rsp"] == 0x000000000027E500
    assert reportInfo.registers["rbp"] == 0x0000000006CF2120
    assert reportInfo.registers["r8"] == 0x000000000027CE88
    assert reportInfo.registers["r9"] == 0x00000000020CC069
    assert reportInfo.registers["r10"] == 0x0000000000000000
    assert reportInfo.registers["r11"] == 0x000000000027E3F0
    assert reportInfo.registers["r12"] == 0x0000000006C0D088
    assert reportInfo.registers["r13"] == 0x0000000006C139AD
    assert reportInfo.registers["r14"] == 0x0000000000000000
    assert reportInfo.registers["r15"] == 0x0000000006C13991

    assert reportInfo.reportAddress == 0x0000000140144E62


def test_CDBSelectorTest2a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    reportData = (FIXTURE_PATH / "cdb-2a-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x0000000140144E62


# Test 2b is for Win10 with 64-bit js debug deterministic shell hitting the assertion
# failure:
#     js_dbg_64_dm_windows_62f79d676e0e!js::GetBytecodeLength+52
#     00007ff7`1e424e62 cc              int     3
def test_CDBParserTestReport2b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-2b-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 25
    assert reportInfo.backtrace[0] == "js::GetBytecodeLength"
    assert reportInfo.backtrace[1] == "js::coverage::LCovSource::writeScript"
    assert (
        reportInfo.backtrace[2]
        == "js::coverage::LCovCompartment::collectCodeCoverageInfo"
    )
    assert reportInfo.backtrace[3] == "GenerateLcovInfo"
    assert reportInfo.backtrace[4] == "js::GetCodeCoverageSummary"
    assert reportInfo.backtrace[5] == "GetLcovInfo"
    assert reportInfo.backtrace[6] == "js::CallJSNative"
    assert reportInfo.backtrace[7] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[8] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[9] == "??"
    assert reportInfo.backtrace[10] == "??"
    assert reportInfo.backtrace[11] == "??"
    assert reportInfo.backtrace[12] == "??"
    assert reportInfo.backtrace[13] == "??"
    assert reportInfo.backtrace[14] == "??"
    assert reportInfo.backtrace[15] == "??"
    assert reportInfo.backtrace[16] == "??"
    assert reportInfo.backtrace[17] == "??"
    assert reportInfo.backtrace[18] == "??"
    assert reportInfo.backtrace[19] == "??"
    assert reportInfo.backtrace[20] == "??"
    assert reportInfo.backtrace[21] == "??"
    assert reportInfo.backtrace[22] == "??"
    assert reportInfo.backtrace[23] == "??"
    assert reportInfo.backtrace[24] == "??"

    assert reportInfo.reportInstruction == "int 3"
    assert reportInfo.registers["rax"] == 0x0000000000000000
    assert reportInfo.registers["rbx"] == 0x0000024DBF40BAAC
    assert reportInfo.registers["rcx"] == 0x00000000FFFFFFFF
    assert reportInfo.registers["rdx"] == 0x0000000000000000
    assert reportInfo.registers["rsi"] == 0x0000024DBF40BA9E
    assert reportInfo.registers["rdi"] == 0x0000024DBF4F2201
    assert reportInfo.registers["rip"] == 0x00007FF71E424E62
    assert reportInfo.registers["rsp"] == 0x000000DE223FE3D0
    assert reportInfo.registers["rbp"] == 0x0000024DBF4F22E0
    assert reportInfo.registers["r8"] == 0x000000DE223FCD78
    assert reportInfo.registers["r9"] == 0x0000024DBEBE0735
    assert reportInfo.registers["r10"] == 0x0000000000000000
    assert reportInfo.registers["r11"] == 0x000000DE223FE240
    assert reportInfo.registers["r12"] == 0x0000024DBF414088
    assert reportInfo.registers["r13"] == 0x0000024DBF40BAAD
    assert reportInfo.registers["r14"] == 0x0000000000000000
    assert reportInfo.registers["r15"] == 0x0000024DBF40BA91

    assert reportInfo.reportAddress == 0x00007FF71E424E62


def test_CDBSelectorTest2b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    reportData = (FIXTURE_PATH / "cdb-2b-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x00007FF71E424E62


# Test 3a is for Win7 with 32-bit js debug deterministic shell reporting:
#     js_dbg_32_dm_windows_62f79d676e0e!js::gc::TenuredCell::arena
#     00f36a63 8b00            mov     eax,dword ptr [eax]
def test_CDBParserTestReport3a():
    config = ProgramConfiguration("test", "x86", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-3a-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 36
    assert reportInfo.backtrace[0] == "js::gc::TenuredCell::arena"
    assert reportInfo.backtrace[1] == "js::TenuringTracer::moveToTenured"
    assert reportInfo.backtrace[2] == "js::TenuringTracer::traverse"
    assert reportInfo.backtrace[3] == "js::DispatchTyped"
    assert reportInfo.backtrace[4] == "DispatchToTracer"
    assert reportInfo.backtrace[5] == "js::TraceRootRange"
    assert reportInfo.backtrace[6] == "js::jit::BaselineFrame::trace"
    assert reportInfo.backtrace[7] == "js::jit::MarkJitActivation"
    assert reportInfo.backtrace[8] == "js::jit::MarkJitActivations"
    assert reportInfo.backtrace[9] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert reportInfo.backtrace[10] == "js::Nursery::doCollection"
    assert reportInfo.backtrace[11] == "js::Nursery::collect"
    assert reportInfo.backtrace[12] == "js::gc::GCRuntime::minorGC"
    assert reportInfo.backtrace[13] == "js::gc::GCRuntime::runDebugGC"
    assert reportInfo.backtrace[14] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert reportInfo.backtrace[15] == "js::gc::GCRuntime::checkAllocatorState"
    assert reportInfo.backtrace[16] == "js::Allocate"
    assert reportInfo.backtrace[17] == "JSObject::create"
    assert reportInfo.backtrace[18] == "NewObject"
    assert reportInfo.backtrace[19] == "js::NewObjectWithGivenTaggedProto"
    assert reportInfo.backtrace[20] == "js::ProxyObject::New"
    assert reportInfo.backtrace[21] == "js::NewProxyObject"
    assert reportInfo.backtrace[22] == "js::Wrapper::New"
    assert reportInfo.backtrace[23] == "js::TransparentObjectWrapper"
    assert reportInfo.backtrace[24] == "JSCompartment::wrap"
    assert reportInfo.backtrace[25] == "JSCompartment::wrap"
    assert reportInfo.backtrace[26] == "js::CrossCompartmentWrapper::call"
    assert reportInfo.backtrace[27] == "js::Proxy::call"
    assert reportInfo.backtrace[28] == "js::proxy_Call"
    assert reportInfo.backtrace[29] == "js::CallJSNative"
    assert reportInfo.backtrace[30] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[31] == "InternalCall"
    assert reportInfo.backtrace[32] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[33] == "??"
    assert reportInfo.backtrace[34] == "EnterIon"
    assert reportInfo.backtrace[35] == "??"

    assert reportInfo.reportInstruction == "mov eax,dword ptr [eax]"
    assert reportInfo.registers["eax"] == 0x2B2FFFF0
    assert reportInfo.registers["ebx"] == 0x0041DE08
    assert reportInfo.registers["ecx"] == 0x2B2B2B2B
    assert reportInfo.registers["edx"] == 0x0A200310
    assert reportInfo.registers["esi"] == 0x0041DC68
    assert reportInfo.registers["edi"] == 0x0A200310
    assert reportInfo.registers["eip"] == 0x00F36A63
    assert reportInfo.registers["esp"] == 0x0041DC04
    assert reportInfo.registers["ebp"] == 0x0041DC2C

    assert reportInfo.reportAddress == 0x00F36A63


def test_CDBSelectorTest3a():
    config = ProgramConfiguration("test", "x86", "windows")

    reportData = (FIXTURE_PATH / "cdb-3a-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x00F36A63


# Test 3b is for Win10 with 32-bit js debug deterministic shell reporting:
#     js_dbg_32_dm_windows_62f79d676e0e!js::gc::TenuredCell::arena+13
#     00ed6a63 8b00            mov     eax,dword ptr [eax]
def test_CDBParserTestReport3b():
    config = ProgramConfiguration("test", "x86", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-3b-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 36
    assert reportInfo.backtrace[0] == "js::gc::TenuredCell::arena"
    assert reportInfo.backtrace[1] == "js::TenuringTracer::moveToTenured"
    assert reportInfo.backtrace[2] == "js::TenuringTracer::traverse"
    assert reportInfo.backtrace[3] == "js::DispatchTyped"
    assert reportInfo.backtrace[4] == "DispatchToTracer"
    assert reportInfo.backtrace[5] == "js::TraceRootRange"
    assert reportInfo.backtrace[6] == "js::jit::BaselineFrame::trace"
    assert reportInfo.backtrace[7] == "js::jit::MarkJitActivation"
    assert reportInfo.backtrace[8] == "js::jit::MarkJitActivations"
    assert reportInfo.backtrace[9] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert reportInfo.backtrace[10] == "js::Nursery::doCollection"
    assert reportInfo.backtrace[11] == "js::Nursery::collect"
    assert reportInfo.backtrace[12] == "js::gc::GCRuntime::minorGC"
    assert reportInfo.backtrace[13] == "js::gc::GCRuntime::runDebugGC"
    assert reportInfo.backtrace[14] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert reportInfo.backtrace[15] == "js::gc::GCRuntime::checkAllocatorState"
    assert reportInfo.backtrace[16] == "js::Allocate"
    assert reportInfo.backtrace[17] == "JSObject::create"
    assert reportInfo.backtrace[18] == "NewObject"
    assert reportInfo.backtrace[19] == "js::NewObjectWithGivenTaggedProto"
    assert reportInfo.backtrace[20] == "js::ProxyObject::New"
    assert reportInfo.backtrace[21] == "js::NewProxyObject"
    assert reportInfo.backtrace[22] == "js::Wrapper::New"
    assert reportInfo.backtrace[23] == "js::TransparentObjectWrapper"
    assert reportInfo.backtrace[24] == "JSCompartment::wrap"
    assert reportInfo.backtrace[25] == "JSCompartment::wrap"
    assert reportInfo.backtrace[26] == "js::CrossCompartmentWrapper::call"
    assert reportInfo.backtrace[27] == "js::Proxy::call"
    assert reportInfo.backtrace[28] == "js::proxy_Call"
    assert reportInfo.backtrace[29] == "js::CallJSNative"
    assert reportInfo.backtrace[30] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[31] == "InternalCall"
    assert reportInfo.backtrace[32] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[33] == "??"
    assert reportInfo.backtrace[34] == "EnterIon"
    assert reportInfo.backtrace[35] == "??"

    assert reportInfo.reportInstruction == "mov eax,dword ptr [eax]"
    assert reportInfo.registers["eax"] == 0x2B2FFFF0
    assert reportInfo.registers["ebx"] == 0x02B2DEB8
    assert reportInfo.registers["ecx"] == 0x2B2B2B2B
    assert reportInfo.registers["edx"] == 0x04200310
    assert reportInfo.registers["esi"] == 0x02B2DD18
    assert reportInfo.registers["edi"] == 0x04200310
    assert reportInfo.registers["eip"] == 0x00ED6A63
    assert reportInfo.registers["esp"] == 0x02B2DCB4
    assert reportInfo.registers["ebp"] == 0x02B2DCDC

    assert reportInfo.reportAddress == 0x00ED6A63


def test_CDBSelectorTest3b():
    config = ProgramConfiguration("test", "x86", "windows")

    reportData = (FIXTURE_PATH / "cdb-3b-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x00ED6A63


# Test 4a is for Win7 with 32-bit js opt deterministic shell reporting:
#     js_32_dm_windows_62f79d676e0e!JSObject::allocKindForTenure
#     00d44c59 8b39            mov     edi,dword ptr [ecx]
def test_CDBParserTestReport4a():
    config = ProgramConfiguration("test", "x86", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-4a-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 54
    assert reportInfo.backtrace[0] == "JSObject::allocKindForTenure"
    assert reportInfo.backtrace[1] == "js::TenuringTracer::moveToTenured"
    assert reportInfo.backtrace[2] == "js::TenuringTraversalFunctor"
    assert reportInfo.backtrace[3] == "js::DispatchTyped"
    assert reportInfo.backtrace[4] == "DispatchToTracer"
    assert reportInfo.backtrace[5] == "js::TraceRootRange"
    assert reportInfo.backtrace[6] == "js::jit::BaselineFrame::trace"
    assert reportInfo.backtrace[7] == "js::jit::MarkJitActivation"
    assert reportInfo.backtrace[8] == "js::jit::MarkJitActivations"
    assert reportInfo.backtrace[9] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert reportInfo.backtrace[10] == "js::Nursery::doCollection"
    assert reportInfo.backtrace[11] == "js::Nursery::collect"
    assert reportInfo.backtrace[12] == "js::gc::GCRuntime::minorGC"
    assert reportInfo.backtrace[13] == "js::gc::GCRuntime::runDebugGC"
    assert reportInfo.backtrace[14] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert reportInfo.backtrace[15] == "js::Allocate"
    assert reportInfo.backtrace[16] == "JSObject::create"
    assert reportInfo.backtrace[17] == "NewObject"
    assert reportInfo.backtrace[18] == "js::NewObjectWithGivenTaggedProto"
    assert reportInfo.backtrace[19] == "js::ProxyObject::New"
    assert reportInfo.backtrace[20] == "js::NewProxyObject"
    assert reportInfo.backtrace[21] == "js::Wrapper::New"
    assert reportInfo.backtrace[22] == "js::TransparentObjectWrapper"
    assert reportInfo.backtrace[23] == "JSCompartment::wrap"
    assert reportInfo.backtrace[24] == "JSCompartment::wrap"
    assert reportInfo.backtrace[25] == "js::CrossCompartmentWrapper::call"
    assert reportInfo.backtrace[26] == "js::Proxy::call"
    assert reportInfo.backtrace[27] == "js::proxy_Call"
    assert reportInfo.backtrace[28] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[29] == "InternalCall"
    assert reportInfo.backtrace[30] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[31] == "je_free"
    assert reportInfo.backtrace[32] == "js::jit::IonCannon"
    assert reportInfo.backtrace[33] == "js::RunScript"
    assert reportInfo.backtrace[34] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[35] == "InternalCall"
    assert reportInfo.backtrace[36] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[37] == "EnterBaseline"
    assert reportInfo.backtrace[38] == "js::jit::EnterBaselineAtBranch"
    assert reportInfo.backtrace[39] == "Interpret"
    assert reportInfo.backtrace[40] == "js::RunScript"
    assert reportInfo.backtrace[41] == "js::ExecuteKernel"
    assert reportInfo.backtrace[42] == "js::Execute"
    assert reportInfo.backtrace[43] == "ExecuteScript"
    assert reportInfo.backtrace[44] == "JS_ExecuteScript"
    assert reportInfo.backtrace[45] == "RunFile"
    assert reportInfo.backtrace[46] == "Process"
    assert reportInfo.backtrace[47] == "ProcessArgs"
    assert reportInfo.backtrace[48] == "Shell"
    assert reportInfo.backtrace[49] == "main"
    assert reportInfo.backtrace[50] == "__scrt_common_main_seh"
    assert reportInfo.backtrace[51] == "BaseThreadInitThunk"
    assert reportInfo.backtrace[52] == "RtlInitializeExceptionChain"
    assert reportInfo.backtrace[53] == "RtlInitializeExceptionChain"

    assert reportInfo.reportInstruction == "mov edi,dword ptr [ecx]"
    assert reportInfo.registers["eax"] == 0x09BFFF01
    assert reportInfo.registers["ebx"] == 0x002ADC18
    assert reportInfo.registers["ecx"] == 0x2B2B2B2B
    assert reportInfo.registers["edx"] == 0x002AE2F0
    assert reportInfo.registers["esi"] == 0x09B00310
    assert reportInfo.registers["edi"] == 0x09B00310
    assert reportInfo.registers["eip"] == 0x00D44C59
    assert reportInfo.registers["esp"] == 0x002ADA8C
    assert reportInfo.registers["ebp"] == 0x002ADC18

    assert reportInfo.reportAddress == 0x00D44C59


def test_CDBSelectorTest4a():
    config = ProgramConfiguration("test", "x86", "windows")

    reportData = (FIXTURE_PATH / "cdb-4a-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x00D44C59


# Test 4b is for Win10 with 32-bit js opt deterministic shell reporting:
#     js_32_dm_windows_62f79d676e0e!JSObject::allocKindForTenure+9
#     00404c59 8b39            mov     edi,dword ptr [ecx]
def test_CDBParserTestReport4b():
    config = ProgramConfiguration("test", "x86", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-4b-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 38
    assert reportInfo.backtrace[0] == "JSObject::allocKindForTenure"
    assert reportInfo.backtrace[1] == "js::TenuringTracer::moveToTenured"
    assert reportInfo.backtrace[2] == "js::TenuringTraversalFunctor"
    assert reportInfo.backtrace[3] == "js::DispatchTyped"
    assert reportInfo.backtrace[4] == "DispatchToTracer"
    assert reportInfo.backtrace[5] == "js::TraceRootRange"
    assert reportInfo.backtrace[6] == "js::jit::BaselineFrame::trace"
    assert reportInfo.backtrace[7] == "js::jit::MarkJitActivation"
    assert reportInfo.backtrace[8] == "js::jit::MarkJitActivations"
    assert reportInfo.backtrace[9] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert reportInfo.backtrace[10] == "js::Nursery::doCollection"
    assert reportInfo.backtrace[11] == "js::Nursery::collect"
    assert reportInfo.backtrace[12] == "js::gc::GCRuntime::minorGC"
    assert reportInfo.backtrace[13] == "js::gc::GCRuntime::runDebugGC"
    assert reportInfo.backtrace[14] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert reportInfo.backtrace[15] == "js::Allocate"
    assert reportInfo.backtrace[16] == "JSObject::create"
    assert reportInfo.backtrace[17] == "NewObject"
    assert reportInfo.backtrace[18] == "js::NewObjectWithGivenTaggedProto"
    assert reportInfo.backtrace[19] == "js::ProxyObject::New"
    assert reportInfo.backtrace[20] == "js::NewProxyObject"
    assert reportInfo.backtrace[21] == "js::Wrapper::New"
    assert reportInfo.backtrace[22] == "js::TransparentObjectWrapper"
    assert reportInfo.backtrace[23] == "JSCompartment::wrap"
    assert reportInfo.backtrace[24] == "JSCompartment::wrap"
    assert reportInfo.backtrace[25] == "js::CrossCompartmentWrapper::call"
    assert reportInfo.backtrace[26] == "js::Proxy::call"
    assert reportInfo.backtrace[27] == "js::proxy_Call"
    assert reportInfo.backtrace[28] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[29] == "InternalCall"
    assert reportInfo.backtrace[30] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[31] == "je_free"
    assert reportInfo.backtrace[32] == "js::jit::IonCannon"
    assert reportInfo.backtrace[33] == "js::RunScript"
    assert reportInfo.backtrace[34] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[35] == "InternalCall"
    assert reportInfo.backtrace[36] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[37] == "EnterBaseline"

    assert reportInfo.reportInstruction == "mov edi,dword ptr [ecx]"
    assert reportInfo.registers["eax"] == 0x02EFFF01
    assert reportInfo.registers["ebx"] == 0x016FDDB8
    assert reportInfo.registers["ecx"] == 0x2B2B2B2B
    assert reportInfo.registers["edx"] == 0x016FE490
    assert reportInfo.registers["esi"] == 0x02E00310
    assert reportInfo.registers["edi"] == 0x02E00310
    assert reportInfo.registers["eip"] == 0x00404C59
    assert reportInfo.registers["esp"] == 0x016FDC2C
    assert reportInfo.registers["ebp"] == 0x016FDDB8

    assert reportInfo.reportAddress == 0x00404C59


def test_CDBSelectorTest4b():
    config = ProgramConfiguration("test", "x86", "windows")

    reportData = (FIXTURE_PATH / "cdb-4b-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x00404C59


# Test 5a is for Win7 with 64-bit js debug deterministic shell reporting:
#     js_dbg_64_dm_windows_62f79d676e0e!js::gc::IsInsideNursery
#     00000001`3f4975db 8b11            mov     edx,dword ptr [rcx]
def test_CDBParserTestReport5a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-5a-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 34
    assert reportInfo.backtrace[0] == "js::gc::IsInsideNursery"
    assert reportInfo.backtrace[1] == "js::gc::TenuredCell::arena"
    assert reportInfo.backtrace[2] == "js::TenuringTracer::moveToTenured"
    assert reportInfo.backtrace[3] == "js::TenuringTracer::traverse"
    assert reportInfo.backtrace[4] == "js::DispatchTyped"
    assert reportInfo.backtrace[5] == "DispatchToTracer"
    assert reportInfo.backtrace[6] == "js::TraceRootRange"
    assert reportInfo.backtrace[7] == "js::jit::BaselineFrame::trace"
    assert reportInfo.backtrace[8] == "js::jit::MarkJitActivation"
    assert reportInfo.backtrace[9] == "js::jit::MarkJitActivations"
    assert reportInfo.backtrace[10] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert reportInfo.backtrace[11] == "js::Nursery::doCollection"
    assert reportInfo.backtrace[12] == "js::Nursery::collect"
    assert reportInfo.backtrace[13] == "js::gc::GCRuntime::minorGC"
    assert reportInfo.backtrace[14] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert reportInfo.backtrace[15] == "js::gc::GCRuntime::checkAllocatorState"
    assert reportInfo.backtrace[16] == "js::Allocate"
    assert reportInfo.backtrace[17] == "JSObject::create"
    assert reportInfo.backtrace[18] == "NewObject"
    assert reportInfo.backtrace[19] == "js::NewObjectWithGivenTaggedProto"
    assert reportInfo.backtrace[20] == "js::ProxyObject::New"
    assert reportInfo.backtrace[21] == "js::NewProxyObject"
    assert reportInfo.backtrace[22] == "js::Wrapper::New"
    assert reportInfo.backtrace[23] == "js::TransparentObjectWrapper"
    assert reportInfo.backtrace[24] == "JSCompartment::wrap"
    assert reportInfo.backtrace[25] == "JSCompartment::wrap"
    assert reportInfo.backtrace[26] == "js::CrossCompartmentWrapper::call"
    assert reportInfo.backtrace[27] == "js::Proxy::call"
    assert reportInfo.backtrace[28] == "js::proxy_Call"
    assert reportInfo.backtrace[29] == "js::CallJSNative"
    assert reportInfo.backtrace[30] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[31] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[32] == "??"
    assert reportInfo.backtrace[33] == "??"

    assert reportInfo.reportInstruction == "mov edx,dword ptr [rcx]"
    assert reportInfo.registers["rax"] == 0x0000000000000001
    assert reportInfo.registers["rbx"] == 0xFFFE2B2B2B2B2B2B
    assert reportInfo.registers["rcx"] == 0xFFFE2B2B2B2FFFE8
    assert reportInfo.registers["rdx"] == 0x0000000000000001
    assert reportInfo.registers["rsi"] == 0x000000000040C078
    assert reportInfo.registers["rdi"] == 0x0000000006A00420
    assert reportInfo.registers["rip"] == 0x000000013F4975DB
    assert reportInfo.registers["rsp"] == 0x000000000040BC40
    assert reportInfo.registers["rbp"] == 0x0000000000000006
    assert reportInfo.registers["r8"] == 0x0000000006633200
    assert reportInfo.registers["r9"] == 0x000000014079B1A0
    assert reportInfo.registers["r10"] == 0x0000000000000031
    assert reportInfo.registers["r11"] == 0x0000000000000033
    assert reportInfo.registers["r12"] == 0xFFFA7FFFFFFFFFFF
    assert reportInfo.registers["r13"] == 0xFFFC000000000000
    assert reportInfo.registers["r14"] == 0x000000000040C078
    assert reportInfo.registers["r15"] == 0x000000014079B1A0

    assert reportInfo.reportAddress == 0x000000013F4975DB


def test_CDBSelectorTest5a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    reportData = (FIXTURE_PATH / "cdb-5a-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x000000013F4975DB


# Test 5b is for Win10 with 64-bit js debug deterministic shell reporting:
#     js_dbg_64_dm_windows_62f79d676e0e!js::gc::IsInsideNursery+1b
#     00007ff7`1dcf75db 8b11            mov     edx,dword ptr [rcx]
def test_CDBParserTestReport5b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-5b-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 34
    assert reportInfo.backtrace[0] == "js::gc::IsInsideNursery"
    assert reportInfo.backtrace[1] == "js::gc::TenuredCell::arena"
    assert reportInfo.backtrace[2] == "js::TenuringTracer::moveToTenured"
    assert reportInfo.backtrace[3] == "js::TenuringTracer::traverse"
    assert reportInfo.backtrace[4] == "js::DispatchTyped"
    assert reportInfo.backtrace[5] == "DispatchToTracer"
    assert reportInfo.backtrace[6] == "js::TraceRootRange"
    assert reportInfo.backtrace[7] == "js::jit::BaselineFrame::trace"
    assert reportInfo.backtrace[8] == "js::jit::MarkJitActivation"
    assert reportInfo.backtrace[9] == "js::jit::MarkJitActivations"
    assert reportInfo.backtrace[10] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert reportInfo.backtrace[11] == "js::Nursery::doCollection"
    assert reportInfo.backtrace[12] == "js::Nursery::collect"
    assert reportInfo.backtrace[13] == "js::gc::GCRuntime::minorGC"
    assert reportInfo.backtrace[14] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert reportInfo.backtrace[15] == "js::gc::GCRuntime::checkAllocatorState"
    assert reportInfo.backtrace[16] == "js::Allocate"
    assert reportInfo.backtrace[17] == "JSObject::create"
    assert reportInfo.backtrace[18] == "NewObject"
    assert reportInfo.backtrace[19] == "js::NewObjectWithGivenTaggedProto"
    assert reportInfo.backtrace[20] == "js::ProxyObject::New"
    assert reportInfo.backtrace[21] == "js::NewProxyObject"
    assert reportInfo.backtrace[22] == "js::Wrapper::New"
    assert reportInfo.backtrace[23] == "js::TransparentObjectWrapper"
    assert reportInfo.backtrace[24] == "JSCompartment::wrap"
    assert reportInfo.backtrace[25] == "JSCompartment::wrap"
    assert reportInfo.backtrace[26] == "js::CrossCompartmentWrapper::call"
    assert reportInfo.backtrace[27] == "js::Proxy::call"
    assert reportInfo.backtrace[28] == "js::proxy_Call"
    assert reportInfo.backtrace[29] == "js::CallJSNative"
    assert reportInfo.backtrace[30] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[31] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[32] == "??"
    assert reportInfo.backtrace[33] == "??"

    assert reportInfo.reportInstruction == "mov edx,dword ptr [rcx]"
    assert reportInfo.registers["rax"] == 0x0000000000000001
    assert reportInfo.registers["rbx"] == 0xFFFE2B2B2B2B2B2B
    assert reportInfo.registers["rcx"] == 0xFFFE2B2B2B2FFFE8
    assert reportInfo.registers["rdx"] == 0x0000000000000001
    assert reportInfo.registers["rsi"] == 0x000000C4A47FC528
    assert reportInfo.registers["rdi"] == 0x0000021699700420
    assert reportInfo.registers["rip"] == 0x00007FF71DCF75DB
    assert reportInfo.registers["rsp"] == 0x000000C4A47FC0F0
    assert reportInfo.registers["rbp"] == 0x0000000000000006
    assert reportInfo.registers["r8"] == 0x0000021699633200
    assert reportInfo.registers["r9"] == 0x00007FF71EFFA590
    assert reportInfo.registers["r10"] == 0x0000000000000031
    assert reportInfo.registers["r11"] == 0x0000000000000033
    assert reportInfo.registers["r12"] == 0xFFFA7FFFFFFFFFFF
    assert reportInfo.registers["r13"] == 0xFFFC000000000000
    assert reportInfo.registers["r14"] == 0x000000C4A47FC528
    assert reportInfo.registers["r15"] == 0x00007FF71EFFA590

    assert reportInfo.reportAddress == 0x00007FF71DCF75DB


def test_CDBSelectorTest5b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    reportData = (FIXTURE_PATH / "cdb-5b-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x00007FF71DCF75DB


# Test 6a is for Win7 with 64-bit js opt deterministic shell reporting:
#     js_64_dm_windows_62f79d676e0e!JSObject::allocKindForTenure
#     00000001`3f869ff3 4c8b01          mov     r8,qword ptr [rcx]
def test_CDBParserTestReport6a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-6a-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 58
    assert reportInfo.backtrace[0] == "JSObject::allocKindForTenure"
    assert reportInfo.backtrace[1] == "js::TenuringTracer::moveToTenured"
    assert reportInfo.backtrace[2] == "js::DispatchTyped"
    assert reportInfo.backtrace[3] == "js::TraceRootRange"
    assert reportInfo.backtrace[4] == "js::jit::BaselineFrame::trace"
    assert reportInfo.backtrace[5] == "js::jit::MarkJitActivation"
    assert reportInfo.backtrace[6] == "js::jit::MarkJitActivations"
    assert reportInfo.backtrace[7] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert reportInfo.backtrace[8] == "js::Nursery::doCollection"
    assert reportInfo.backtrace[9] == "js::Nursery::collect"
    assert reportInfo.backtrace[10] == "js::gc::GCRuntime::minorGC"
    assert reportInfo.backtrace[11] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert reportInfo.backtrace[12] == "js::Allocate"
    assert reportInfo.backtrace[13] == "JSObject::create"
    assert reportInfo.backtrace[14] == "NewObject"
    assert reportInfo.backtrace[15] == "js::NewObjectWithGivenTaggedProto"
    assert reportInfo.backtrace[16] == "js::ProxyObject::New"
    assert reportInfo.backtrace[17] == "js::NewProxyObject"
    assert reportInfo.backtrace[18] == "js::TransparentObjectWrapper"
    assert reportInfo.backtrace[19] == "JSCompartment::wrap"
    assert reportInfo.backtrace[20] == "JSCompartment::wrap"
    assert reportInfo.backtrace[21] == "js::CrossCompartmentWrapper::call"
    assert reportInfo.backtrace[22] == "js::Proxy::call"
    assert reportInfo.backtrace[23] == "js::proxy_Call"
    assert reportInfo.backtrace[24] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[25] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[26] == "??"
    assert reportInfo.backtrace[27] == "??"
    assert reportInfo.backtrace[28] == "??"
    assert reportInfo.backtrace[29] == "??"
    assert reportInfo.backtrace[30] == "??"
    assert reportInfo.backtrace[31] == "??"
    assert reportInfo.backtrace[32] == "??"
    assert reportInfo.backtrace[33] == "??"
    assert reportInfo.backtrace[34] == "??"
    assert reportInfo.backtrace[35] == "??"
    assert reportInfo.backtrace[36] == "??"
    assert reportInfo.backtrace[37] == "??"
    assert reportInfo.backtrace[38] == "??"
    assert reportInfo.backtrace[39] == "??"
    assert reportInfo.backtrace[40] == "??"
    assert reportInfo.backtrace[41] == "??"
    assert reportInfo.backtrace[42] == "??"
    assert reportInfo.backtrace[43] == "??"
    assert reportInfo.backtrace[44] == "??"
    assert reportInfo.backtrace[45] == "??"
    assert reportInfo.backtrace[46] == "??"
    assert reportInfo.backtrace[47] == "??"
    assert reportInfo.backtrace[48] == "??"
    assert reportInfo.backtrace[49] == "??"
    assert reportInfo.backtrace[50] == "??"
    assert reportInfo.backtrace[51] == "??"
    assert reportInfo.backtrace[52] == "??"
    assert reportInfo.backtrace[53] == "??"
    assert reportInfo.backtrace[54] == "??"
    assert reportInfo.backtrace[55] == "??"
    assert reportInfo.backtrace[56] == "??"
    assert reportInfo.backtrace[57] == "??"

    assert reportInfo.reportInstruction == "mov r8,qword ptr [rcx]"
    assert reportInfo.registers["rax"] == 0x000000013FCFEEF0
    assert reportInfo.registers["rbx"] == 0x0000000008D00420
    assert reportInfo.registers["rcx"] == 0x2B2B2B2B2B2B2B2B
    assert reportInfo.registers["rdx"] == 0x000000000681B940
    assert reportInfo.registers["rsi"] == 0x000000000034C7B0
    assert reportInfo.registers["rdi"] == 0x0000000008D00420
    assert reportInfo.registers["rip"] == 0x000000013F869FF3
    assert reportInfo.registers["rsp"] == 0x000000000034C4B0
    assert reportInfo.registers["rbp"] == 0xFFFE000000000000
    assert reportInfo.registers["r8"] == 0x000000000034C5B0
    assert reportInfo.registers["r9"] == 0x000000000001FFFC
    assert reportInfo.registers["r10"] == 0x000000000000061D
    assert reportInfo.registers["r11"] == 0x000000000685A000
    assert reportInfo.registers["r12"] == 0x000000013FD23A98
    assert reportInfo.registers["r13"] == 0xFFFA7FFFFFFFFFFF
    assert reportInfo.registers["r14"] == 0x000000000034D550
    assert reportInfo.registers["r15"] == 0x0000000000000003

    assert reportInfo.reportAddress == 0x000000013F869FF3


def test_CDBSelectorTest6a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    reportData = (FIXTURE_PATH / "cdb-6a-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x000000013F869FF3


# Test 6b is for Win10 with 64-bit js opt deterministic shell reporting:
#     js_64_dm_windows_62f79d676e0e!JSObject::allocKindForTenure+13
#     00007ff7`4d469ff3 4c8b01          mov     r8,qword ptr [rcx]
def test_CDBParserTestReport6b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-6b-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 58
    assert reportInfo.backtrace[0] == "JSObject::allocKindForTenure"
    assert reportInfo.backtrace[1] == "js::TenuringTracer::moveToTenured"
    assert reportInfo.backtrace[2] == "js::DispatchTyped"
    assert reportInfo.backtrace[3] == "js::TraceRootRange"
    assert reportInfo.backtrace[4] == "js::jit::BaselineFrame::trace"
    assert reportInfo.backtrace[5] == "js::jit::MarkJitActivation"
    assert reportInfo.backtrace[6] == "js::jit::MarkJitActivations"
    assert reportInfo.backtrace[7] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert reportInfo.backtrace[8] == "js::Nursery::doCollection"
    assert reportInfo.backtrace[9] == "js::Nursery::collect"
    assert reportInfo.backtrace[10] == "js::gc::GCRuntime::minorGC"
    assert reportInfo.backtrace[11] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert reportInfo.backtrace[12] == "js::Allocate"
    assert reportInfo.backtrace[13] == "JSObject::create"
    assert reportInfo.backtrace[14] == "NewObject"
    assert reportInfo.backtrace[15] == "js::NewObjectWithGivenTaggedProto"
    assert reportInfo.backtrace[16] == "js::ProxyObject::New"
    assert reportInfo.backtrace[17] == "js::NewProxyObject"
    assert reportInfo.backtrace[18] == "js::TransparentObjectWrapper"
    assert reportInfo.backtrace[19] == "JSCompartment::wrap"
    assert reportInfo.backtrace[20] == "JSCompartment::wrap"
    assert reportInfo.backtrace[21] == "js::CrossCompartmentWrapper::call"
    assert reportInfo.backtrace[22] == "js::Proxy::call"
    assert reportInfo.backtrace[23] == "js::proxy_Call"
    assert reportInfo.backtrace[24] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[25] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[26] == "??"
    assert reportInfo.backtrace[27] == "??"
    assert reportInfo.backtrace[28] == "??"
    assert reportInfo.backtrace[29] == "??"
    assert reportInfo.backtrace[30] == "??"
    assert reportInfo.backtrace[31] == "??"
    assert reportInfo.backtrace[32] == "??"
    assert reportInfo.backtrace[33] == "??"
    assert reportInfo.backtrace[34] == "??"
    assert reportInfo.backtrace[35] == "??"
    assert reportInfo.backtrace[36] == "??"
    assert reportInfo.backtrace[37] == "??"
    assert reportInfo.backtrace[38] == "??"
    assert reportInfo.backtrace[39] == "??"
    assert reportInfo.backtrace[40] == "??"
    assert reportInfo.backtrace[41] == "??"
    assert reportInfo.backtrace[42] == "??"
    assert reportInfo.backtrace[43] == "??"
    assert reportInfo.backtrace[44] == "??"
    assert reportInfo.backtrace[45] == "??"
    assert reportInfo.backtrace[46] == "??"
    assert reportInfo.backtrace[47] == "??"
    assert reportInfo.backtrace[48] == "??"
    assert reportInfo.backtrace[49] == "??"
    assert reportInfo.backtrace[50] == "??"
    assert reportInfo.backtrace[51] == "??"
    assert reportInfo.backtrace[52] == "??"
    assert reportInfo.backtrace[53] == "??"
    assert reportInfo.backtrace[54] == "??"
    assert reportInfo.backtrace[55] == "??"
    assert reportInfo.backtrace[56] == "??"
    assert reportInfo.backtrace[57] == "??"

    assert reportInfo.reportInstruction == "mov r8,qword ptr [rcx]"
    assert reportInfo.registers["rax"] == 0x00007FF74D8FEE30
    assert reportInfo.registers["rbx"] == 0x00000285EF400420
    assert reportInfo.registers["rcx"] == 0x2B2B2B2B2B2B2B2B
    assert reportInfo.registers["rdx"] == 0x00000285EF21B940
    assert reportInfo.registers["rsi"] == 0x000000E87FBFC340
    assert reportInfo.registers["rdi"] == 0x00000285EF400420
    assert reportInfo.registers["rip"] == 0x00007FF74D469FF3
    assert reportInfo.registers["rsp"] == 0x000000E87FBFC040
    assert reportInfo.registers["rbp"] == 0xFFFE000000000000
    assert reportInfo.registers["r8"] == 0x00000E87FBFC140
    assert reportInfo.registers["r9"] == 0x00000000001FFFC
    assert reportInfo.registers["r10"] == 0x0000000000000649
    assert reportInfo.registers["r11"] == 0x00000285EF25A000
    assert reportInfo.registers["r12"] == 0x00007FF74D9239A0
    assert reportInfo.registers["r13"] == 0xFFFA7FFFFFFFFFFF
    assert reportInfo.registers["r14"] == 0x000000E87FBFD0E0
    assert reportInfo.registers["r15"] == 0x0000000000000003

    assert reportInfo.reportAddress == 0x00007FF74D469FF3


def test_CDBSelectorTest6b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    reportData = (FIXTURE_PATH / "cdb-6b-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x00007FF74D469FF3


# Test 7 is for Windows Server 2012 R2 with 32-bit js debug deterministic shell:
#     +205
#     25d80b01 cc              int     3
def test_CDBParserTestReport7():
    config = ProgramConfiguration("test", "x86", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-7c-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 46
    assert reportInfo.backtrace[0] == "??"
    assert reportInfo.backtrace[1] == "arena_run_dalloc"
    assert reportInfo.backtrace[2] == "EnterIon"
    assert reportInfo.backtrace[3] == "js::jit::IonCannon"
    assert reportInfo.backtrace[4] == "js::RunScript"
    assert reportInfo.backtrace[5] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[6] == "InternalCall"
    assert reportInfo.backtrace[7] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[8] == "??"
    assert reportInfo.backtrace[9] == "je_free"
    assert reportInfo.backtrace[10] == "EnterIon"
    assert reportInfo.backtrace[11] == "js::jit::IonCannon"
    assert reportInfo.backtrace[12] == "js::RunScript"
    assert reportInfo.backtrace[13] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[14] == "InternalCall"
    assert reportInfo.backtrace[15] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[16] == "EnterIon"
    assert reportInfo.backtrace[17] == "js::jit::IonCannon"
    assert reportInfo.backtrace[18] == "js::RunScript"
    assert reportInfo.backtrace[19] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[20] == "InternalCall"
    assert reportInfo.backtrace[21] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[22] == "??"
    assert reportInfo.backtrace[23] == "??"
    assert reportInfo.backtrace[24] == "EnterIon"
    assert reportInfo.backtrace[25] == "js::jit::IonCannon"
    assert reportInfo.backtrace[26] == "js::RunScript"
    assert reportInfo.backtrace[27] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[28] == "InternalCall"
    assert reportInfo.backtrace[29] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[30] == "EnterBaseline"
    assert reportInfo.backtrace[31] == "js::jit::EnterBaselineMethod"
    assert reportInfo.backtrace[32] == "js::RunScript"
    assert reportInfo.backtrace[33] == "js::ExecuteKernel"
    assert reportInfo.backtrace[34] == "js::Execute"
    assert reportInfo.backtrace[35] == "ExecuteScript"
    assert reportInfo.backtrace[36] == "JS_ExecuteScript"
    assert reportInfo.backtrace[37] == "RunFile"
    assert reportInfo.backtrace[38] == "Process"
    assert reportInfo.backtrace[39] == "ProcessArgs"
    assert reportInfo.backtrace[40] == "Shell"
    assert reportInfo.backtrace[41] == "main"
    assert reportInfo.backtrace[42] == "__scrt_common_main_seh"
    assert reportInfo.backtrace[43] == "kernel32"
    assert reportInfo.backtrace[44] == "ntdll"
    assert reportInfo.backtrace[45] == "ntdll"

    assert reportInfo.reportInstruction == "int 3"
    assert reportInfo.registers["eax"] == 0x00C8A948
    assert reportInfo.registers["ebx"] == 0x0053E32C
    assert reportInfo.registers["ecx"] == 0x6802052B
    assert reportInfo.registers["edx"] == 0x00000000
    assert reportInfo.registers["esi"] == 0x25D8094B
    assert reportInfo.registers["edi"] == 0x0053E370
    assert reportInfo.registers["eip"] == 0x25D80B01
    assert reportInfo.registers["esp"] == 0x0053E370
    assert reportInfo.registers["ebp"] == 0xFFE00000

    assert reportInfo.reportAddress == 0x25D80B01


def test_CDBSelectorTest7():
    config = ProgramConfiguration("test", "x86", "windows")

    reportData = (FIXTURE_PATH / "cdb-7c-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x25D80B01


# Test 8 is for Windows Server 2012 R2 with 32-bit js debug profiling deterministic
# shell:
#     js_dbg_32_prof_dm_windows_42c95d88aaaa!js::jit::Range::upper+3d [
#         c:\users\administrator\trees\mozilla-central\js\src\jit\rangeanalysis.h @ 578]
#     0142865d cc              int     3
def test_CDBParserTestReport8():
    config = ProgramConfiguration("test", "x86", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-8c-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 1
    assert reportInfo.backtrace[0] == "??"

    assert reportInfo.reportInstruction == "int 3"
    assert reportInfo.registers["eax"] == 0x00000000
    assert reportInfo.registers["ebx"] == 0x00000000
    assert reportInfo.registers["ecx"] == 0x73F1705D
    assert reportInfo.registers["edx"] == 0x00EA9210
    assert reportInfo.registers["esi"] == 0x00000383
    assert reportInfo.registers["edi"] == 0x0A03D110
    assert reportInfo.registers["eip"] == 0x0142865D
    assert reportInfo.registers["esp"] == 0x00EAA780
    assert reportInfo.registers["ebp"] == 0x00EAA7EC

    assert reportInfo.reportAddress == 0x0142865D


def test_CDBSelectorTest8():
    config = ProgramConfiguration("test", "x86", "windows")

    reportData = (FIXTURE_PATH / "cdb-8c-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x0142865D


# Test 9 is for Windows Server 2012 R2 with 32-bit js opt profiling shell:
#     +1d8
#     0f2bb4f3 cc              int     3
def test_CDBParserTestReport9():
    config = ProgramConfiguration("test", "x86", "windows")

    reportInfo = CDBReportInfo(
        [], [], config, (FIXTURE_PATH / "cdb-9c-reportlog.txt").read_text().splitlines()
    )

    assert len(reportInfo.backtrace) == 44
    assert reportInfo.backtrace[0] == "??"
    assert reportInfo.backtrace[1] == "??"
    assert reportInfo.backtrace[2] == "js::AddTypePropertyId"
    assert reportInfo.backtrace[3] == "js::jit::EnterBaselineMethod"
    assert reportInfo.backtrace[4] == "??"
    assert reportInfo.backtrace[5] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[6] == "InternalCall"
    assert reportInfo.backtrace[7] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[8] == "??"
    assert reportInfo.backtrace[9] == "js::Activation::Activation"
    assert reportInfo.backtrace[10] == "EnterBaseline"
    assert reportInfo.backtrace[11] == "??"
    assert reportInfo.backtrace[12] == "js::RunScript"
    assert reportInfo.backtrace[13] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[14] == "InternalCall"
    assert reportInfo.backtrace[15] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[16] == "??"
    assert reportInfo.backtrace[17] == "??"
    assert reportInfo.backtrace[18] == "js::Activation::Activation"
    assert reportInfo.backtrace[19] == "EnterBaseline"
    assert reportInfo.backtrace[20] == "??"
    assert reportInfo.backtrace[21] == "js::RunScript"
    assert reportInfo.backtrace[22] == "js::InternalCallOrConstruct"
    assert reportInfo.backtrace[23] == "InternalCall"
    assert reportInfo.backtrace[24] == "js::jit::DoCallFallback"
    assert reportInfo.backtrace[25] == "??"
    assert reportInfo.backtrace[26] == "EnterBaseline"
    assert reportInfo.backtrace[27] == "??"
    assert reportInfo.backtrace[28] == "EnterBaseline"
    assert reportInfo.backtrace[29] == "js::jit::EnterBaselineMethod"
    assert reportInfo.backtrace[30] == "js::RunScript"
    assert reportInfo.backtrace[31] == "js::ExecuteKernel"
    assert reportInfo.backtrace[32] == "js::Execute"
    assert reportInfo.backtrace[33] == "ExecuteScript"
    assert reportInfo.backtrace[34] == "JS_ExecuteScript"
    assert reportInfo.backtrace[35] == "RunFile"
    assert reportInfo.backtrace[36] == "Process"
    assert reportInfo.backtrace[37] == "ProcessArgs"
    assert reportInfo.backtrace[38] == "Shell"
    assert reportInfo.backtrace[39] == "main"
    assert reportInfo.backtrace[40] == "__scrt_common_main_seh"
    assert reportInfo.backtrace[41] == "kernel32"
    assert reportInfo.backtrace[42] == "ntdll"
    assert reportInfo.backtrace[43] == "ntdll"

    assert reportInfo.reportInstruction == "int 3"
    assert reportInfo.registers["eax"] == 0x00000020
    assert reportInfo.registers["ebx"] == 0x00B0EA18
    assert reportInfo.registers["ecx"] == 0x00000400
    assert reportInfo.registers["edx"] == 0x73E74F80
    assert reportInfo.registers["esi"] == 0xFFFFFF8C
    assert reportInfo.registers["edi"] == 0x00B0EA00
    assert reportInfo.registers["eip"] == 0x0F2BB4F3
    assert reportInfo.registers["esp"] == 0x00B0EA00
    assert reportInfo.registers["ebp"] == 0x00B0EAB0

    assert reportInfo.reportAddress == 0x0F2BB4F3


def test_CDBSelectorTest9():
    config = ProgramConfiguration("test", "x86", "windows")

    reportData = (FIXTURE_PATH / "cdb-9c-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x0F2BB4F3


# Test 10 is for Windows Server 2012 R2 with 32-bit js opt profiling shell:
#     +82
#     1c2fbbb0 cc              int     3
def test_CDBParserTestReport10():
    config = ProgramConfiguration("test", "x86", "windows")

    reportInfo = CDBReportInfo(
        [],
        [],
        config,
        (FIXTURE_PATH / "cdb-10c-reportlog.txt").read_text().splitlines(),
    )

    assert len(reportInfo.backtrace) == 5
    assert reportInfo.backtrace[0] == "??"
    assert reportInfo.backtrace[1] == "js::jit::PrepareOsrTempData"
    assert reportInfo.backtrace[2] == "??"
    assert reportInfo.backtrace[3] == "js::AddTypePropertyId"
    assert reportInfo.backtrace[4] == "JSObject::makeLazyGroup"

    assert reportInfo.reportInstruction == "int 3"
    assert reportInfo.registers["eax"] == 0x06FDA948
    assert reportInfo.registers["ebx"] == 0x020DE8DC
    assert reportInfo.registers["ecx"] == 0x5F7B6461
    assert reportInfo.registers["edx"] == 0x00000000
    assert reportInfo.registers["esi"] == 0x1C2FBAAB
    assert reportInfo.registers["edi"] == 0x020DE910
    assert reportInfo.registers["eip"] == 0x1C2FBBB0
    assert reportInfo.registers["esp"] == 0x020DE910
    assert reportInfo.registers["ebp"] == 0x00000018

    assert reportInfo.reportAddress == 0x1C2FBBB0


def test_CDBSelectorTest10():
    config = ProgramConfiguration("test", "x86", "windows")

    reportData = (FIXTURE_PATH / "cdb-10c-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x1C2FBBB0


# Test 11 is for Windows Server 2012 R2 with 32-bit js debug profiling deterministic
# shell:
#     js_dbg_32_prof_dm_windows_42c95d88aaaa!js::jit::Range::upper+3d [
#         c:\users\administrator\trees\mozilla-central\js\src\jit\rangeanalysis.h @ 578]
#     0156865d cc              int     3
def test_CDBParserTestReport11():
    config = ProgramConfiguration("test", "x86", "windows")

    reportInfo = CDBReportInfo(
        [],
        [],
        config,
        (FIXTURE_PATH / "cdb-11c-reportlog.txt").read_text().splitlines(),
    )

    assert len(reportInfo.backtrace) == 1
    assert reportInfo.backtrace[0] == "??"

    assert reportInfo.reportInstruction == "int 3"
    assert reportInfo.registers["eax"] == 0x00000000
    assert reportInfo.registers["ebx"] == 0x00000000
    assert reportInfo.registers["ecx"] == 0x738F705D
    assert reportInfo.registers["edx"] == 0x00E7B0E0
    assert reportInfo.registers["esi"] == 0x00000383
    assert reportInfo.registers["edi"] == 0x0BA37110
    assert reportInfo.registers["eip"] == 0x0156865D
    assert reportInfo.registers["esp"] == 0x00E7C650
    assert reportInfo.registers["ebp"] == 0x00E7C6BC

    assert reportInfo.reportAddress == 0x0156865D


def test_CDBSelectorTest11():
    config = ProgramConfiguration("test", "x86", "windows")

    reportData = (FIXTURE_PATH / "cdb-11c-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x0156865D


# Test 12 is for Windows Server 2012 R2 with 32-bit js opt profiling deterministic shell
#     +1d8
#     1fa0b7f8 cc              int     3
def test_CDBParserTestReport12():
    config = ProgramConfiguration("test", "x86", "windows")

    reportInfo = CDBReportInfo(
        [],
        [],
        config,
        (FIXTURE_PATH / "cdb-12c-reportlog.txt").read_text().splitlines(),
    )

    assert len(reportInfo.backtrace) == 4
    assert reportInfo.backtrace[0] == "??"
    assert reportInfo.backtrace[1] == "??"
    assert reportInfo.backtrace[2] == "js::AddTypePropertyId"
    assert reportInfo.backtrace[3] == "JSObject::makeLazyGroup"

    assert reportInfo.reportInstruction == "int 3"
    assert reportInfo.registers["eax"] == 0x00000020
    assert reportInfo.registers["ebx"] == 0x0044EA78
    assert reportInfo.registers["ecx"] == 0x00000000
    assert reportInfo.registers["edx"] == 0x73BF4F80
    assert reportInfo.registers["esi"] == 0xFFFFFF8C
    assert reportInfo.registers["edi"] == 0x0044EA50
    assert reportInfo.registers["eip"] == 0x1FA0B7F8
    assert reportInfo.registers["esp"] == 0x0044EA50
    assert reportInfo.registers["ebp"] == 0x0044EB00

    assert reportInfo.reportAddress == 0x1FA0B7F8


def test_CDBSelectorTest12():
    config = ProgramConfiguration("test", "x86", "windows")

    reportData = (FIXTURE_PATH / "cdb-12c-reportlog.txt").read_text().splitlines()

    reportInfo = ReportInfo.fromRawReportData([], [], config, reportData)
    assert reportInfo.reportAddress == 0x1FA0B7F8


def test_UBSanParserTestReport1():
    config = ProgramConfiguration("test", "x86", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_ubsan_signed_int_overflow.txt").read_text().splitlines(),
    )
    assert reportInfo.createShortSignature() == (
        "UndefinedBehaviorSanitizer: "
        "codec/decoder/core/inc/dec_golomb.h:182:37: "
        "runtime error: signed integer overflow: -2147483648 - "
        "1 cannot be represented in type 'int'"
    )
    assert len(reportInfo.backtrace) == 12
    assert reportInfo.backtrace[0] == "WelsDec::BsGetUe"
    assert reportInfo.backtrace[9] == "_start"
    assert reportInfo.backtrace[11] == "Lex< >"
    assert reportInfo.reportAddress is None


def test_UBSanParserTestReport2():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_ubsan_div_by_zero.txt").read_text().splitlines(),
    )
    assert reportInfo.createShortSignature() == (
        "UndefinedBehaviorSanitizer: src/opus_demo.c:870:40: "
        "runtime error: division by zero"
    )
    assert len(reportInfo.backtrace) == 3
    assert reportInfo.backtrace[0] == "main"
    assert reportInfo.reportAddress is None


def test_UBSanParserTestReport3():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_ubsan_missing_pattern.txt").read_text().splitlines(),
    )
    assert reportInfo.createShortSignature() == "No report detected"
    assert len(reportInfo.backtrace) == 0
    assert reportInfo.reportAddress is None


def test_UBSanParserTestReport4():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_ubsan_generic_report.txt").read_text().splitlines(),
    )
    assert reportInfo.createShortSignature() == ("[@ mozilla::dom::ToJSValue]")
    assert len(reportInfo.backtrace) == 2
    assert reportInfo.backtrace[0] == "mozilla::dom::ToJSValue"
    assert reportInfo.backtrace[1] == "js::jit::DoCallFallback"

    assert reportInfo.reportAddress == 0x000000004141
    assert reportInfo.registers["pc"] == 0x7F070B805037
    assert reportInfo.registers["bp"] == 0x7F06626006B0
    assert reportInfo.registers["sp"] == 0x7F0662600680


def test_UBSanParserTestReport5():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_ubsan_div_by_zero_no_trace.txt")
        .read_text()
        .splitlines(),
    )
    assert reportInfo.createShortSignature() == (
        "UndefinedBehaviorSanitizer: src/opus_demo.c:870:40: "
        "runtime error: division by zero"
    )
    assert not reportInfo.backtrace
    assert reportInfo.reportAddress is None


def test_UBSanParserTestReport6():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_ubsan_generic_report_no_trace.txt")
        .read_text()
        .splitlines(),
    )
    assert reportInfo.createShortSignature() == ("[@ ??]")
    assert not reportInfo.backtrace
    assert reportInfo.reportAddress == 0x000000004141
    assert reportInfo.registers["pc"] == 0x7F070B805037
    assert reportInfo.registers["bp"] == 0x7F06626006B0
    assert reportInfo.registers["sp"] == 0x7F0662600680


def test_RustParserTests1():
    """test RUST_BACKTRACE=1 is parsed correctly"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_rust_sample_1.txt").read_text().splitlines(),
    )
    assert isinstance(reportInfo, RustReportInfo)
    assert reportInfo.createShortSignature() == (
        "thread 'StyleThread#2' panicked at "
        "'assertion failed: self.get_data().is_some()', "
        "/home/worker/workspace/build/src/servo/components/"
        "style/gecko/wrapper.rs:976"
    )
    assert len(reportInfo.backtrace) == 20
    assert (
        reportInfo.backtrace[0]
        == "std::sys::imp::backtrace::tracing::imp::unwind_backtrace"
    )
    assert reportInfo.backtrace[14] == (
        "<style::gecko::traversal::RecalcStyleOnly<'recalc> as "
        "style::traversal::DomTraversal<style::gecko::wrapper::"
        "GeckoElement<'le>>>::process_preorder"
    )
    assert reportInfo.backtrace[19] == "<unknown>"
    assert reportInfo.reportAddress == 0


def test_RustParserTests2():
    """test RUST_BACKTRACE=full is parsed correctly"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_rust_sample_2.txt").read_text().splitlines(),
    )
    assert isinstance(reportInfo, RustReportInfo)
    assert reportInfo.createShortSignature() == (
        "thread 'StyleThread#3' panicked at "
        "'assertion failed: self.get_data().is_some()', "
        "/home/worker/workspace/build/src/servo/components/style/"
        "gecko/wrapper.rs:1040"
    )
    assert len(reportInfo.backtrace) == 21
    assert (
        reportInfo.backtrace[0]
        == "std::sys::imp::backtrace::tracing::imp::unwind_backtrace"
    )
    assert reportInfo.backtrace[14] == (
        "<style::gecko::traversal::RecalcStyleOnly<'recalc> as "
        "style::traversal::DomTraversal<style::gecko::wrapper::"
        "GeckoElement<'le>>>::process_preorder"
    )
    assert reportInfo.backtrace[20] == "<unknown>"
    assert reportInfo.reportAddress == 0
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_rust_sample_3.txt").read_text().splitlines(),
    )
    assert isinstance(reportInfo, RustReportInfo)
    assert reportInfo.createShortSignature() == (
        "thread 'StyleThread#2' panicked at "
        "'already mutably borrowed', /home/worker/workspace/build/"
        "src/third_party/rust/atomic_refcell/src/lib.rs:161"
    )
    assert len(reportInfo.backtrace) == 7
    assert (
        reportInfo.backtrace[0]
        == "std::sys::imp::backtrace::tracing::imp::unwind_backtrace"
    )
    assert reportInfo.backtrace[3] == "std::panicking::rust_panic_with_hook"
    assert reportInfo.backtrace[6] == (
        "<style::values::specified::color::Color as style::values::computed"
        "::ToComputedValue>::to_computed_value"
    )
    assert reportInfo.reportAddress == 0


def test_RustParserTests3():
    """test rust backtraces are weakly found, ie. minidump output wins even if it comes
    after"""
    config = ProgramConfiguration("test", "x86-64", "win")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_rust_sample_4.txt").read_text().splitlines(),
    )
    assert isinstance(reportInfo, MinidumpReportInfo)
    assert reportInfo.createShortSignature() == (
        r"thread 'StyleThread#2' panicked at "
        r"'already mutably borrowed', "
        r"Z:\build\build\src\third_party\rust\atomic_"
        r"refcell\src\lib.rs:161"
    )
    assert len(reportInfo.backtrace) == 4
    assert reportInfo.backtrace[0] == "std::panicking::rust_panic_with_hook"
    assert reportInfo.backtrace[1] == "std::panicking::begin_panic<&str>"
    assert reportInfo.backtrace[2] == "atomic_refcell::AtomicBorrowRef::do_panic"
    assert (
        reportInfo.backtrace[3]
        == "style::values::specified::color::{{impl}}::to_computed_value"
    )
    assert reportInfo.reportAddress == 0x7FFC41F2F276


def test_RustParserTests4():
    """test another rust backtrace"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_rust_sample_5.txt").read_text().splitlines(),
    )
    assert isinstance(reportInfo, RustReportInfo)
    assert reportInfo.createShortSignature() == (
        "thread 'RenderBackend' panicked at 'called "
        "`Option::unwrap()` on a `None` value', /checkout/src/"
        "libcore/option.rs:335:20"
    )
    assert len(reportInfo.backtrace) == 3
    assert (
        reportInfo.backtrace[0]
        == "std::sys::imp::backtrace::tracing::imp::unwind_backtrace"
    )
    assert reportInfo.backtrace[1] == "std::panicking::default_hook::{{closure}}"
    assert reportInfo.backtrace[2] == "std::panicking::default_hook"
    assert reportInfo.reportAddress == 0


def test_RustParserTests5():
    """test multi-line with minidump trace in sterror rust backtrace"""
    auxData = [
        "OS|Linux|0.0.0 Linux ... x86_64",
        "CPU|amd64|family 6 model 63 stepping 2|8",
        "GPU|||",
        "Report|SIGSEGV|0x0|0",
        (
            "0|0|firefox|mozalloc_abort|hg:hg.mozilla.org/mozilla-central:memory"
            "/mozalloc/mozalloc_abort.cpp:6d82e132348f|33|0x0"
        ),
        (
            "0|1|firefox|abort|hg:hg.mozilla.org/mozilla-central:memory/mozalloc"
            "/mozalloc_abort.cpp:6d82e132348f|80|0x5"
        ),
        (
            "0|2|libxul.so|panic_abort::__rust_start_panic|git:github.com/rust-lang"
            "/rust:src/libpanic_abort/"
            "lib.rs:05e2e1c41414e8fc73d0f267ea8dab1a3eeeaa99|59|0x5"
        ),
    ]
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        (FIXTURE_PATH / "trace_rust_sample_6.txt").read_text().splitlines(),
        config,
        auxData,
    )
    assert isinstance(reportInfo, MinidumpReportInfo)
    assert (
        "panicked at 'assertion failed: `(left == right)`"
        in reportInfo.createShortSignature()
    )
    assert len(reportInfo.backtrace) == 3
    assert reportInfo.backtrace[0] == "mozalloc_abort"
    assert reportInfo.backtrace[1] == "abort"
    assert reportInfo.backtrace[2] == "panic_abort::__rust_start_panic"
    assert reportInfo.reportAddress == 0


def test_RustParserTests6():
    """test parsing rust assertion failure backtrace"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        (FIXTURE_PATH / "trace_rust_sample_6.txt").read_text().splitlines(),
        config,
        [],
    )
    assert isinstance(reportInfo, RustReportInfo)
    assert (
        "panicked at 'assertion failed: `(left == right)`"
        in reportInfo.createShortSignature()
    )
    assert len(reportInfo.backtrace) == 4
    assert reportInfo.backtrace[1] == "std::sys_common::backtrace::_print"
    assert reportInfo.reportAddress == 0


def test_MinidumpModuleInStackTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_minidump_swrast.txt").read_text().splitlines(),
    )
    assert reportInfo.backtrace[0] == "??"
    assert reportInfo.backtrace[1] == "swrast_dri.so+0x470ecc"


def test_LSanParserTestLeakDetected():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_lsan_leak_detected.txt").read_text().splitlines(),
    )
    assert reportInfo.createShortSignature() == ("LeakSanitizer: [@ malloc]")
    assert len(reportInfo.backtrace) == 4
    assert reportInfo.backtrace[0] == "malloc"
    assert reportInfo.backtrace[1] == "moz_xmalloc"
    assert reportInfo.backtrace[2] == "operator new"
    assert reportInfo.backtrace[3] == "mozilla::net::nsStandardURL::StartClone"
    assert reportInfo.reportAddress is None


def test_TSanParserSimpleLeakTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "tsan-simple-leak-report.txt").read_text().splitlines(),
    )

    assert reportInfo.createShortSignature() == (
        "ThreadSanitizer: thread leak [@ pthread_create]"
    )

    assert len(reportInfo.backtrace) == 2
    assert reportInfo.backtrace[0] == "pthread_create"
    assert reportInfo.backtrace[1] == "main"

    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress is None


def test_TSanParserSimpleRaceTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    for fn in ["tsan-simple-race-report.txt", "tsan-simple-race-report-swapped.txt"]:
        reportInfo = ReportInfo.fromRawReportData(
            [], [], config, (FIXTURE_PATH / fn).read_text().splitlines()
        )

        assert reportInfo.createShortSignature() == (
            "ThreadSanitizer: data race [@ foo1] vs. [@ foo2]"
        )

        assert len(reportInfo.backtrace) == 8
        assert reportInfo.backtrace[0] == "foo1"
        assert reportInfo.backtrace[1] == "bar1"
        assert reportInfo.backtrace[2] == "Thread1"
        assert reportInfo.backtrace[3] == "foo2"
        assert reportInfo.backtrace[4] == "bar2"

        assert reportInfo.reportInstruction is None
        assert reportInfo.reportAddress is None


def test_TSanParserLockReportTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "tsan-lock-report.txt").read_text().splitlines()
    )

    assert reportInfo.createShortSignature() == (
        "ThreadSanitizer: lock-order-inversion (potential deadlock) [@ PR_Lock]"
    )

    assert len(reportInfo.backtrace) == 12
    assert reportInfo.backtrace[0] == "pthread_mutex_lock"
    assert reportInfo.backtrace[1] == "PR_Lock"
    assert reportInfo.backtrace[2] == "sftk_hasAttribute"
    assert reportInfo.backtrace[3] == "sftk_CopyObject"
    assert reportInfo.backtrace[4] == "pthread_mutex_lock"

    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress is None


def test_TSanParserTestReport():
    config = ProgramConfiguration("test", "x86", "linux")

    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_tsan_report.txt").read_text().splitlines(),
    )
    assert reportInfo.createShortSignature() == "[@ mozalloc_abort]"
    assert len(reportInfo.backtrace) == 6
    assert reportInfo.backtrace[0] == "mozalloc_abort"
    assert reportInfo.backtrace[1] == "mozalloc_handle_oom"
    assert reportInfo.backtrace[2] == "GeckoHandleOOM"
    assert reportInfo.backtrace[3] == "gkrust_shared::oom_hook::hook"
    assert reportInfo.backtrace[4] == "swrast_dri.so+0x75dc33"
    assert reportInfo.backtrace[5] == "<missing>"

    assert reportInfo.reportAddress == 0
    assert reportInfo.registers["pc"] == 0x559ED71AA5E3
    assert reportInfo.registers["bp"] == 0x033
    assert reportInfo.registers["sp"] == 0x7FE1A51BCF00


def test_TSanParserTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "tsan-report.txt").read_text().splitlines()
    )

    assert reportInfo.createShortSignature() == (
        "ThreadSanitizer: data race "
        "[@ js::ProtectedData<js::CheckMainThread"
        "<(js::AllowedHelperThread)0>, unsigned long>::operator++] "
        "vs. [@ js::gc::GCRuntime::majorGCCount]"
    )

    assert len(reportInfo.backtrace) == 146
    assert reportInfo.backtrace[1] == "js::gc::GCRuntime::incMajorGcNumber"
    assert reportInfo.backtrace[5] == "js::gc::GCRuntime::gcIfNeededAtAllocation"

    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress is None


def test_TSanParserTestClang14():
    config = ProgramConfiguration("test", "x86-64", "linux")

    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_tsan_clang14.txt").read_text().splitlines(),
    )
    assert (
        "ThreadSanitizer: data race [@ operator new] vs. [@ pthread_mutex_lock]"
        == reportInfo.createShortSignature()
    )
    assert reportInfo.reportAddress is None
    assert reportInfo.reportInstruction is None
    assert len(reportInfo.backtrace) == 166
    assert reportInfo.backtrace[0] == "operator new"
    assert reportInfo.backtrace[5:9] == [
        "pthread_mutex_lock",
        "libLLVM-12.so.1+0xb6f3ea",
        "nsThread::ThreadFunc",
        "_pt_root",
    ]


def test_ValgrindCJMParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-cjm-01.txt").read_text().splitlines()
    )

    assert reportInfo.createShortSignature() == (
        "Valgrind: Conditional jump or move depends on uninitialised value(s) "
        "[@ PyObject_Free]"
    )
    assert len(reportInfo.backtrace) == 7
    assert reportInfo.backtrace[0] == "PyObject_Free"
    assert reportInfo.backtrace[1] == "/usr/bin/python3.6"
    assert reportInfo.backtrace[3] == "main"
    assert reportInfo.backtrace[-1] == "main"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress is None

    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-cjm-02.txt").read_text().splitlines()
    )

    assert reportInfo.createShortSignature() == (
        "Valgrind: Conditional jump or move depends on uninitialised value(s) "
        "[@ strlen]"
    )
    assert len(reportInfo.backtrace) == 5
    assert reportInfo.backtrace[0] == "strlen"
    assert reportInfo.backtrace[1] == "puts"
    assert reportInfo.backtrace[3] == "(below main)"
    assert reportInfo.backtrace[4] == "/home/user/a.out"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress is None


def test_ValgrindIRWParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-ir-01.txt").read_text().splitlines()
    )

    assert (
        reportInfo.createShortSignature()
        == "Valgrind: Invalid read of size 4 [@ blah_func]"
    )
    assert len(reportInfo.backtrace) == 4
    assert reportInfo.backtrace[0] == "blah_func"
    assert reportInfo.backtrace[1] == "main"
    assert reportInfo.backtrace[-1] == "asdf"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress == 0xBADF00D

    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-ir-02.txt").read_text().splitlines()
    )

    assert (
        reportInfo.createShortSignature() == "Valgrind: Invalid read of size 4 [@ main]"
    )
    assert len(reportInfo.backtrace) == 1
    assert reportInfo.backtrace[0] == "main"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress == 0x5204068

    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-iw-01.txt").read_text().splitlines()
    )

    assert (
        reportInfo.createShortSignature()
        == "Valgrind: Invalid write of size 8 [@ memcpy]"
    )
    assert len(reportInfo.backtrace) == 2
    assert reportInfo.backtrace[0] == "memcpy"
    assert reportInfo.backtrace[1] == "main"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress == 0x41414141


def test_ValgrindUUVParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-uuv-01.txt").read_text().splitlines()
    )

    assert (
        reportInfo.createShortSignature()
        == "Valgrind: Use of uninitialised value of size 8 [@ foo<123>::Init]"
    )
    assert len(reportInfo.backtrace) == 5
    assert reportInfo.backtrace[0] == "foo<123>::Init"
    assert reportInfo.backtrace[
        1
    ], "bar::func<bar::Init()::$_0, Promise<type1, type2 == true> >::Run"
    assert reportInfo.backtrace[2] == "non-virtual thunk to Run"
    assert reportInfo.backtrace[-1] == "posix_memalign"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress is None


def test_ValgrindIFParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-if-01.txt").read_text().splitlines()
    )

    assert (
        reportInfo.createShortSignature()
        == "Valgrind: Invalid free() / delete / delete[] / realloc() [@ free]"
    )
    assert len(reportInfo.backtrace) == 4
    assert reportInfo.backtrace[0] == "free"
    assert reportInfo.backtrace[1] == "main"
    assert reportInfo.backtrace[-1] == "main"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress == 0x43F2931

    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-if-02.txt").read_text().splitlines()
    )

    assert (
        reportInfo.createShortSignature()
        == "Valgrind: Invalid free() / delete / delete[] / realloc() [@ free]"
    )
    assert len(reportInfo.backtrace) == 6
    assert reportInfo.backtrace[0] == "free"
    assert reportInfo.backtrace[1] == "main"
    assert reportInfo.backtrace[-1] == "main"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress == 0x5204040

    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-if-03.txt").read_text().splitlines()
    )

    assert (
        reportInfo.createShortSignature()
        == "Valgrind: Invalid free() / delete / delete[] / realloc() [@ free]"
    )
    assert len(reportInfo.backtrace) == 2
    assert reportInfo.backtrace[0] == "free"
    assert reportInfo.backtrace[1] == "main"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress == 0xBADF00D


def test_ValgrindSDOParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-sdo-01.txt").read_text().splitlines()
    )

    assert reportInfo.createShortSignature() == (
        "Valgrind: Source and destination overlap [@ memcpy]"
    )
    assert len(reportInfo.backtrace) == 2
    assert reportInfo.backtrace[0] == "memcpy"
    assert reportInfo.backtrace[1] == "main"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress is None


def test_ValgrindSCParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-sc-01.txt").read_text().splitlines()
    )

    assert reportInfo.createShortSignature() == (
        "Valgrind: Syscall param write(buf) points to uninitialised byte(s) [@ write]"
    )
    assert len(reportInfo.backtrace) == 6
    assert reportInfo.backtrace[0] == "write"
    assert reportInfo.backtrace[1] == "main"
    assert reportInfo.backtrace[-1] == "main"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress == 0x522E040

    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-sc-02.txt").read_text().splitlines()
    )

    assert reportInfo.createShortSignature() == (
        "Valgrind: Syscall param socketcall.sendto(msg) points to uninitialised byte(s)"
        " [@ send]"
    )
    assert len(reportInfo.backtrace) == 5
    assert reportInfo.backtrace[0] == "send"
    assert reportInfo.backtrace[2] == "start_thread"
    assert reportInfo.backtrace[-1] == "start_thread"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress == 0x5E7B6B4


def test_ValgrindNMParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-nm-01.txt").read_text().splitlines()
    )

    assert reportInfo.createShortSignature() == (
        "Valgrind: Argument 'size' of function malloc has a fishy (possibly negative) "
        "value: -1 [@ malloc]"
    )
    assert len(reportInfo.backtrace) == 2
    assert reportInfo.backtrace[0] == "malloc"
    assert reportInfo.backtrace[1] == "main"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress is None


def test_ValgrindPTParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-pt-01.txt").read_text().splitlines()
    )

    assert reportInfo.createShortSignature() == (
        "Valgrind: Process terminating with default action of signal 11 (SIGSEGV) "
        "[@ strlen]"
    )
    assert len(reportInfo.backtrace) == 3
    assert reportInfo.backtrace[0] == "strlen"
    assert reportInfo.backtrace[2] == "main"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress is None


def test_ValgrindLeakParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-leak-01.txt").read_text().splitlines()
    )

    assert reportInfo.createShortSignature() == (
        "Valgrind: 102,400 bytes in 1,024 blocks are definitely lost [@ malloc]"
    )
    assert len(reportInfo.backtrace) == 3
    assert reportInfo.backtrace[0] == "malloc"
    assert reportInfo.backtrace[2] == "main"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress is None

    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [], [], config, (FIXTURE_PATH / "valgrind-leak-02.txt").read_text().splitlines()
    )

    assert reportInfo.createShortSignature() == (
        "Valgrind: 16 bytes in 1 blocks are possibly lost [@ malloc]"
    )
    assert len(reportInfo.backtrace) == 3
    assert reportInfo.backtrace[0] == "malloc"
    assert reportInfo.backtrace[2] == "main"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress is None


def test_SanitizerSoftRssLimitHeapProfile():
    """test that heap profile given after soft rss limit is exceeded
    is used in place of the (useless) SEGV stack"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_asan_soft_rss_heap_report.txt").read_text().splitlines(),
    )

    assert reportInfo.createShortSignature() == "[@ __interceptor_calloc]"
    assert len(reportInfo.backtrace) == 153
    assert reportInfo.backtrace[0] == "__interceptor_calloc"
    assert (
        reportInfo.backtrace[8] == "webrender_bindings::moz2d_renderer::rasterize_blob"
    )
    assert reportInfo.backtrace[-1] == "wl_display_dispatch_queue_pending"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress == 40


def test_SanitizerHardRssLimitHeapProfile():
    """test that heap profile given after hard rss limit is exceeded
    is used in place of the (useless) SEGV stack"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    reportInfo = ReportInfo.fromRawReportData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_asan_hard_rss_heap_report.txt").read_text().splitlines(),
    )

    assert reportInfo.createShortSignature() == (
        "AddressSanitizer: hard rss limit exhausted"
    )
    assert len(reportInfo.backtrace) == 32
    assert reportInfo.backtrace[0] == "__interceptor_realloc"
    assert reportInfo.backtrace[9] == "webrender::image_tiling::for_each_tile_in_range"
    assert reportInfo.backtrace[-1] == "start_thread"
    assert reportInfo.reportInstruction is None
    assert reportInfo.reportAddress is None


def test_unicode_escape():
    """test that unicode special and control characters are escaped"""

    @unicode_escape_result
    def testfunc():
        return """ü\ufffdシ\u008dAن"""

    assert testfunc() == r"""ü\u{fffd}シ\u{8d}Aن"""
