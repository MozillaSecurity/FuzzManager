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
from FTB.Signatures.CrashInfo import (
    AppleCrashInfo,
    ASanCrashInfo,
    CDBCrashInfo,
    CrashInfo,
    GDBCrashInfo,
    MinidumpCrashInfo,
    NoCrashInfo,
    RustCrashInfo,
    int32,
    unicode_escape_result,
)
from FTB.Signatures.CrashSignature import CrashSignature

FIXTURE_PATH = Path(__file__).parent / "fixtures"


def test_ASanParserTestAccessViolation():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashInfo = ASanCrashInfo(
        [],
        (FIXTURE_PATH / "trace_asan_access_violation.txt").read_text().splitlines(),
        config,
    )
    assert len(crashInfo.backtrace) == 3
    assert crashInfo.backtrace[0] == "nsCSSFrameConstructor::WipeContainingBlock"
    assert crashInfo.backtrace[1] == "nsCSSFrameConstructor::ContentAppended"
    assert crashInfo.backtrace[2] == "mozilla::RestyleManager::ProcessRestyledFrames"

    assert crashInfo.crashAddress == 0x50
    assert crashInfo.registers["pc"] == 0x7FFA9A30C9E7
    assert crashInfo.registers["sp"] == 0x00F9915F0940
    assert crashInfo.registers["bp"] == 0x00F9915F0A20


def test_ASanParserTestCrash():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = ASanCrashInfo(
        [], (FIXTURE_PATH / "trace_asan_segv.txt").read_text().splitlines(), config
    )
    assert len(crashInfo.backtrace) == 9
    assert crashInfo.backtrace[0] == "js::AbstractFramePtr::asRematerializedFrame"
    assert crashInfo.backtrace[2] == "EvalInFrame"
    assert crashInfo.backtrace[3] == "js::CallJSNative"
    assert crashInfo.backtrace[6] == "js::jit::DoCallFallback"
    assert (
        crashInfo.backtrace[7] == "/usr/lib/x86_64-linux-gnu/dri/swrast_dri.so+0x67edd0"
    )
    assert crashInfo.backtrace[8] == "<missing>"

    assert crashInfo.crashAddress == 0x00000014
    assert crashInfo.registers["pc"] == 0x0810845F
    assert crashInfo.registers["sp"] == 0xFFC57860
    assert crashInfo.registers["bp"] == 0xFFC57F18


def test_ASanParserTestCrashWithWarning():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = ASanCrashInfo(
        [],
        (FIXTURE_PATH / "trace_asan_segv_with_warning.txt").read_text().splitlines(),
        config,
    )
    assert len(crashInfo.backtrace) == 7
    assert crashInfo.backtrace[0] == "js::AbstractFramePtr::asRematerializedFrame"
    assert crashInfo.backtrace[2] == "EvalInFrame"
    assert crashInfo.backtrace[3] == "js::CallJSNative"

    assert crashInfo.crashAddress == 0x00000014
    assert crashInfo.registers["pc"] == 0x0810845F
    assert crashInfo.registers["sp"] == 0xFFC57860
    assert crashInfo.registers["bp"] == 0xFFC57F18


def test_ASanParserTestFailedAlloc():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo(
        [],
        (FIXTURE_PATH / "trace_asan_failed_alloc.txt").read_text().splitlines(),
        config,
    )
    assert len(crashInfo.backtrace) == 12
    assert crashInfo.backtrace[0] == "__asan::AsanCheckFailed"
    assert crashInfo.backtrace[7] == "oc_state_frarray_init"

    assert crashInfo.crashAddress is None
    assert not crashInfo.registers

    assert (
        "AddressSanitizer failed to allocate 0x6003a000 (1610850304) bytes of "
        "LargeMmapAllocator (error code: 12) [@ __asan::AsanCheckFailed]"
    ) == crashInfo.createShortSignature()


def test_ASanParserTestAllocSize():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo(
        [],
        (FIXTURE_PATH / "trace_asan_alloc_size.txt").read_text().splitlines(),
        config,
    )
    assert len(crashInfo.backtrace) == 1
    assert crashInfo.backtrace[0] == "malloc"

    assert crashInfo.crashAddress is None
    assert not crashInfo.registers

    assert (
        "AddressSanitizer: requested allocation size exceeds maximum"
        " supported size [@ malloc]"
    ) == crashInfo.createShortSignature()


def test_ASanParserTestHeapCrash():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = ASanCrashInfo(
        [],
        (FIXTURE_PATH / "trace_asan_heap_crash.txt").read_text().splitlines(),
        config,
    )
    assert len(crashInfo.backtrace) == 0

    assert crashInfo.crashAddress == 0x00000019
    assert crashInfo.registers["pc"] == 0xF718072E
    assert crashInfo.registers["sp"] == 0xFF87D130
    assert crashInfo.registers["bp"] == 0x000006A1

    assert crashInfo.createShortSignature() == "[@ ??]"


def test_ASanParserTestUAF():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo(
        [], (FIXTURE_PATH / "trace_asan_uaf.txt").read_text().splitlines(), config
    )
    assert len(crashInfo.backtrace) == 23
    assert crashInfo.backtrace[0] == "void mozilla::PodCopy<char16_t>"
    assert crashInfo.backtrace[4] == "JSFunction::native"

    assert crashInfo.crashAddress == 0x7FD766C42800

    assert (
        "AddressSanitizer: heap-use-after-free [@ void mozilla::PodCopy<char16_t>] "
        "with READ of size 6143520"
    ) == crashInfo.createShortSignature()


def test_ASanParserTestInvalidFree():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo(
        [],
        (FIXTURE_PATH / "trace_asan_invalid_free.txt").read_text().splitlines(),
        config,
    )
    assert len(crashInfo.backtrace) == 1
    assert crashInfo.backtrace[0] == "__interceptor_free"

    assert crashInfo.crashAddress == 0x62A00006C200

    assert (
        "AddressSanitizer: attempting free on address which was not malloc()-ed "
        "[@ __interceptor_free]"
    ) == crashInfo.createShortSignature()


def test_ASanParserTestOOM():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo(
        [], (FIXTURE_PATH / "trace_asan_oom.txt").read_text().splitlines(), config
    )
    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "operator new"
    assert crashInfo.backtrace[1] == (
        "std::vector<"
        "std::pair<unsigned short, llvm::LegalizeActions::LegalizeAction>, "
        "std::allocator<"
        "std::pair<unsigned short, llvm::LegalizeActions::LegalizeAction> "
        "> >::operator="
    )

    assert crashInfo.crashAddress is None

    assert (
        "AddressSanitizer: allocator is out of memory trying to allocate 0x24 bytes "
        "[@ operator new]"
    ) == crashInfo.createShortSignature()


def test_ASanParserTestOOM2():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo(
        [],
        [
            "==5712==ERROR: AddressSanitizer: out of memory: allocator is trying to "
            "allocate 0x16000001090000 bytes",
            "    #0 0x5cab97fe69fd in operator new(unsigned long) /builds/worker/"
            "fetches/llvm-project/compiler-rt/lib/asan/asan_new_delete.cpp:86:3",
        ],
        config,
    )
    assert len(crashInfo.backtrace) == 1
    assert crashInfo.backtrace[0] == "operator new"
    assert crashInfo.crashAddress is None

    assert (
        "AddressSanitizer: out of memory: allocator is trying to allocate "
        "0x16000001090000 bytes [@ operator new]"
    ) == crashInfo.createShortSignature()


def test_ASanParserTestDebugAssertion():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo(
        [],
        (FIXTURE_PATH / "trace_asan_debug_assertion.txt").read_text().splitlines(),
        config,
    )
    assert len(crashInfo.backtrace) == 8
    assert crashInfo.backtrace[0] == "nsCycleCollector::CollectWhite"
    assert (
        crashInfo.backtrace[6]
        == "mozilla::DefaultDelete<ScopedXPCOMStartup>::operator()"
    )

    assert crashInfo.crashAddress == 0x0

    assert (
        "Assertion failure: false (An assert from the graphics logger), at "
        "/builds/slave/m-cen-l64-asan-d-0000000000000/build/src/gfx/2d/Logging.h:521"
    ) == crashInfo.createShortSignature()


@pytest.mark.parametrize(
    "stderr_path, crash_data_path",
    [
        (None, "trace_asan_segv.txt"),
        ("trace_asan_uaf.txt", None),
        (None, "trace_asan_segv_with_warning.txt"),
        (None, "trace_tsan_crash.txt"),
        (None, "trace_ubsan_generic_crash.txt"),
    ],
)
def test_ASanDetectionTest(stderr_path, crash_data_path):
    config = ProgramConfiguration("test", "x86", "linux")
    stderr = "" if stderr_path is None else (FIXTURE_PATH / stderr_path).read_text()
    crash_data = (
        "" if crash_data_path is None else (FIXTURE_PATH / crash_data_path).read_text()
    )
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        stderr.splitlines(),
        config,
        auxCrashData=crash_data.splitlines(),
    )
    assert isinstance(crashInfo, ASanCrashInfo)


def test_ASanParserTestParamOverlap():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo(
        [],
        (FIXTURE_PATH / "trace_asan_memcpy_param_overlap.txt").read_text().splitlines(),
        config,
    )
    assert crashInfo.crashAddress is None
    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "__asan_memcpy"
    assert crashInfo.backtrace[1] == "S32_Opaque_BlitRow32"
    assert crashInfo.createShortSignature() == (
        "AddressSanitizer: memcpy-param-overlap: memory ranges overlap "
        "[@ __asan_memcpy]"
    )

    crashInfo = ASanCrashInfo(
        [],
        (FIXTURE_PATH / "trace_asan_strcat_param_overlap.txt").read_text().splitlines(),
        config,
    )
    assert crashInfo.crashAddress is None
    assert len(crashInfo.backtrace) == 1
    assert crashInfo.backtrace[0] == "__interceptor_strcat"
    assert crashInfo.createShortSignature() == (
        "AddressSanitizer: strcat-param-overlap: memory ranges overlap "
        "[@ __interceptor_strcat]"
    )


def test_ASanParserTestMultiTrace():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo(
        [], (FIXTURE_PATH / "trace_asan_multiple.txt").read_text().splitlines(), config
    )
    assert crashInfo.crashAddress == 0x7F637B59CFFC
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "mozilla::ipc::Shmem::OpenExisting"
    assert crashInfo.backtrace[3] == "CreateThread"
    assert "[@ mozilla::ipc::Shmem::OpenExisting]" == crashInfo.createShortSignature()


def test_ASanParserTestTruncatedTrace():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo(
        [], (FIXTURE_PATH / "trace_asan_truncated.txt").read_text().splitlines(), config
    )

    # Make sure we parsed it as a crash, but without a backtrace
    assert len(crashInfo.backtrace) == 0
    assert crashInfo.crashAddress == 0x0

    # Confirm that generating a crash signature will fail
    crashSig = crashInfo.createCrashSignature()
    assert crashSig is None
    assert "Insufficient data" in crashInfo.failureReason


def test_ASanParserTestClang14():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo(
        [], (FIXTURE_PATH / "trace_asan_clang14.txt").read_text().splitlines(), config
    )
    assert crashInfo.crashAddress == 0x03E800004610
    assert crashInfo.backtrace == [
        "raise",
        "abort",
        "llvm::report_fatal_error",
        "llvm::report_fatal_error",
    ]
    assert "[@ raise]" == crashInfo.createShortSignature()


def test_GDBParserTestCrash():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = GDBCrashInfo(
        [], (FIXTURE_PATH / "trace_gdb_sample_1.txt").read_text().splitlines(), config
    )
    assert len(crashInfo.backtrace) == 8
    assert crashInfo.backtrace[0] == "internalAppend<js::ion::MDefinition*>"
    assert crashInfo.backtrace[2] == "js::ion::MPhi::addInput"
    assert crashInfo.backtrace[6] == "processCfgStack"

    assert crashInfo.registers["eax"] == 0x0
    assert crashInfo.registers["ebx"] == 0x8962FF4
    assert crashInfo.registers["eip"] == 0x818BC33


def test_GDBParserTestCrashAddress():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo1 = GDBCrashInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_crash_addr_1.txt").read_text().splitlines(),
        config,
    )
    crashInfo2 = GDBCrashInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_crash_addr_2.txt").read_text().splitlines(),
        config,
    )
    crashInfo3 = GDBCrashInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_crash_addr_3.txt").read_text().splitlines(),
        config,
    )
    crashInfo4 = GDBCrashInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_crash_addr_4.txt").read_text().splitlines(),
        config,
    )
    crashInfo5 = GDBCrashInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_crash_addr_5.txt").read_text().splitlines(),
        config,
    )

    assert crashInfo1.crashAddress == 0x1
    assert crashInfo2.crashAddress == 0x0
    assert crashInfo3.crashAddress == 0xFFFFFFFFFFFFFFA0
    assert crashInfo4.crashAddress == 0x3EF29D14
    assert crashInfo5.crashAddress == 0x87AFA014


def test_GDBParserTestCrashAddressSimple():
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
        GDBCrashInfo.calculateCrashAddress("mov    %rbx,0x10(%rax)", registerMap64)
        == 0x10
    )
    assert (
        GDBCrashInfo.calculateCrashAddress("mov    %ebx,0x10(%eax)", registerMap32)
        == 0x10
    )

    # Overflow tests
    assert (
        GDBCrashInfo.calculateCrashAddress("mov    %rax,0x10(%rbx)", registerMap64)
        == 0xF
    )
    assert (
        GDBCrashInfo.calculateCrashAddress("mov    %eax,0x10(%ebx)", registerMap32)
        == 0xF
    )

    assert (
        GDBCrashInfo.calculateCrashAddress("mov    %rbx,-0x10(%rax)", registerMap64)
        == -16
    )
    assert (
        GDBCrashInfo.calculateCrashAddress("mov    %ebx,-0x10(%eax)", registerMap32)
        == -16
    )

    # Scalar test
    assert GDBCrashInfo.calculateCrashAddress("movl   $0x7b,0x0", registerMap32) == 0x0

    # Real world examples
    # Note: The crash address here can also be 0xf7600000 because the double quadword
    # move can fail on the second 8 bytes if the source address is not 16-byte aligned
    assert GDBCrashInfo.calculateCrashAddress(
        "movdqu 0x40(%ecx),%xmm4", registerMap32
    ) == int32(0xF75FFFF8)

    # Again, this is an unaligned access and the crash can be at 0x7ffff6700000
    # or 0x7ffff6700000 - 4
    assert (
        GDBCrashInfo.calculateCrashAddress(
            "mov    -0x4(%rdi,%rsi,2),%eax", registerMap64
        )
        == 0x7FFFF66FFFFE
    )


def test_GDBParserTestRegression1():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo1 = GDBCrashInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_regression_1.txt").read_text().splitlines(),
        config,
    )

    assert crashInfo1.backtrace[0] == "js::ScriptedIndirectProxyHandler::defineProperty"
    assert crashInfo1.backtrace[1] == "js::SetPropertyIgnoringNamedGetter"


def test_GDBParserTestCrashAddressRegression2():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo2 = GDBCrashInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_regression_2.txt").read_text().splitlines(),
        config,
    )

    assert crashInfo2.crashAddress == 0xFFFD579C


def test_GDBParserTestCrashAddressRegression3():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo3 = GDBCrashInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_regression_3.txt").read_text().splitlines(),
        config,
    )

    assert crashInfo3.crashAddress == 0x7FFFFFFFFFFF


def test_GDBParserTestCrashAddressRegression4():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo4 = GDBCrashInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_regression_4.txt").read_text().splitlines(),
        config,
    )

    assert crashInfo4.crashAddress == 0x0


def test_GDBParserTestCrashAddressRegression5():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo5 = GDBCrashInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_regression_5.txt").read_text().splitlines(),
        config,
    )

    assert crashInfo5.crashAddress == 0xFFFD573C


def test_GDBParserTestCrashAddressRegression6():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo6 = GDBCrashInfo(
        [],
        (FIXTURE_PATH / "trace_gdb_regression_6.txt").read_text().splitlines(),
        config,
    )

    assert crashInfo6.crashAddress == 0xF7673132


def test_GDBParserTestCrashAddressRegression7():
    config = ProgramConfiguration("test", "x86", "linux")

    # This used to fail because CrashInfo.fromRawCrashData fails to detect a GDB trace
    crashInfo7 = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_7.txt").read_text().splitlines(),
    )

    assert crashInfo7.backtrace[1] == "js::ScopeIter::settle"


def test_GDBParserTestCrashAddressRegression8():
    config = ProgramConfiguration("test", "x86", "linux")

    # This used to fail because CrashInfo.fromRawCrashData fails to detect a GDB trace
    crashInfo8 = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_8.txt").read_text().splitlines(),
    )

    assert (
        crashInfo8.backtrace[2]
        == "js::jit::AutoLockSimulatorCache::AutoLockSimulatorCache"
    )
    assert crashInfo8.backtrace[3] == "<signal handler called>"
    assert crashInfo8.backtrace[4] == "??"
    assert crashInfo8.backtrace[5] == "js::jit::CheckICacheLocked"


def test_GDBParserTestCrashAddressRegression9():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo9 = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_9.txt").read_text().splitlines(),
    )
    assert crashInfo9.crashInstruction == "call   0x8120ca0"


def test_GDBParserTestCrashAddressRegression10():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo10 = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_10.txt").read_text().splitlines(),
    )
    assert crashInfo10.crashInstruction == "(bad)"
    assert crashInfo10.crashAddress == 0x7FF7F20C1F81


def test_GDBParserTestCrashAddressRegression11():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo11 = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_11.txt").read_text().splitlines(),
    )
    assert crashInfo11.crashInstruction == "callq  *0xa8(%rax)"
    assert crashInfo11.crashAddress == 0x7FF7F2091032


def test_GDBParserTestCrashAddressRegression12():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo12 = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_12.txt").read_text().splitlines(),
    )
    assert crashInfo12.backtrace[0] == "js::SavedStacks::insertFrames"
    assert crashInfo12.backtrace[1] == "js::SavedStacks::saveCurrentStack"
    assert crashInfo12.backtrace[2] == "JS::CaptureCurrentStack"
    assert crashInfo12.backtrace[3] == "CaptureStack"


def test_GDBParserTestCrashAddressRegression13():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo13 = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_gdb_regression_13.txt").read_text().splitlines(),
    )
    assert crashInfo13.backtrace[0] == "JSScript::global"
    assert crashInfo13.backtrace[1] == "js::AbstractFramePtr::global"
    assert crashInfo13.backtrace[5] == "js::jit::HandleException"
    assert crashInfo13.backtrace[6] == "??"

    assert crashInfo13.crashInstruction == "pushl  0x10(%eax)"
    assert crashInfo13.crashAddress == 0xE5E5E5F5


def test_CrashSignatureOutputTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashSignature1 = '{ "symptoms" : [ { "type" : "output", "value" : "test" } ] }'
    crashSignature1Neg = (
        '{ "symptoms" : [ { "type" : "output", "src" : "stderr", "value" : "test" } ] }'
    )
    crashSignature2 = (
        '{ "symptoms" : [ { "type" : "output", "src" : "stderr", "value" : { '
        '"value" : "^fest$", "matchType" : "pcre" } } ] }'
    )

    outputSignature1 = CrashSignature(crashSignature1)
    outputSignature1Neg = CrashSignature(crashSignature1Neg)
    outputSignature2 = CrashSignature(crashSignature2)

    gdbOutput = []
    stdout = []
    stderr = []

    stdout.append("Foo")
    stdout.append("Bartester")
    stdout.append("Baz")
    stderr.append("hackfest")

    crashInfo = CrashInfo.fromRawCrashData(
        stdout, stderr, config, auxCrashData=gdbOutput
    )

    assert isinstance(crashInfo, NoCrashInfo)

    # Ensure we match on stdout/err if nothing is specified
    assert outputSignature1.matches(crashInfo)

    # Don't match stdout if stderr is specified
    assert not outputSignature1Neg.matches(crashInfo)

    # Check that we're really using PCRE
    assert not outputSignature2.matches(crashInfo)

    # Add something the PCRE should match, then retry
    stderr.append("fest")
    crashInfo = CrashInfo.fromRawCrashData(
        stdout, stderr, config, auxCrashData=gdbOutput
    )
    assert outputSignature2.matches(crashInfo)


def test_CrashSignatureAddressTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashSignature1 = (
        '{ "symptoms" : [ { "type" : "crashAddress", "address" : "< 0x1000" } ] }'
    )
    crashSignature1Neg = (
        '{ "symptoms" : [ { "type" : "crashAddress", "address" : "0x1000" } ] }'
    )
    addressSig1 = CrashSignature(crashSignature1)
    addressSig1Neg = CrashSignature(crashSignature1Neg)

    crashInfo1 = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_gdb_sample_1.txt").read_text().splitlines(),
    )
    crashInfo3 = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_gdb_sample_3.txt").read_text().splitlines(),
    )

    assert isinstance(crashInfo1, GDBCrashInfo)

    assert addressSig1.matches(crashInfo1)
    assert not addressSig1Neg.matches(crashInfo1)

    # For crashInfo3, we don't have a crash address. Ensure we don't match
    assert not addressSig1.matches(crashInfo3)
    assert not addressSig1Neg.matches(crashInfo3)


def test_CrashSignatureRegisterTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashSignature1 = {"symptoms": [{"type": "instruction", "registerNames": ["r14"]}]}
    crashSignature1Neg = {
        "symptoms": [{"type": "instruction", "registerNames": ["r14", "rax"]}]
    }
    crashSignature2 = {"symptoms": [{"type": "instruction", "instructionName": "mov"}]}
    crashSignature2Neg = {
        "symptoms": [{"type": "instruction", "instructionName": "cmp"}]
    }
    crashSignature3 = {
        "symptoms": [
            {
                "type": "instruction",
                "instructionName": "mov",
                "registerNames": ["r14", "rbx"],
            }
        ]
    }
    crashSignature3Neg = {
        "symptoms": [
            {
                "type": "instruction",
                "instructionName": "mov",
                "registerNames": ["r14", "rax"],
            }
        ]
    }

    instructionSig1 = CrashSignature(json.dumps(crashSignature1))
    instructionSig1Neg = CrashSignature(json.dumps(crashSignature1Neg))

    instructionSig2 = CrashSignature(json.dumps(crashSignature2))
    instructionSig2Neg = CrashSignature(json.dumps(crashSignature2Neg))

    instructionSig3 = CrashSignature(json.dumps(crashSignature3))
    instructionSig3Neg = CrashSignature(json.dumps(crashSignature3Neg))

    crashInfo2 = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_gdb_sample_2.txt").read_text().splitlines(),
    )
    crashInfo3 = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_gdb_sample_3.txt").read_text().splitlines(),
    )

    assert isinstance(crashInfo2, GDBCrashInfo)
    assert isinstance(crashInfo3, GDBCrashInfo)

    assert instructionSig1.matches(crashInfo2)
    assert not instructionSig1Neg.matches(crashInfo2)

    assert instructionSig2.matches(crashInfo2)
    assert not instructionSig2Neg.matches(crashInfo2)

    assert instructionSig3.matches(crashInfo2)
    assert not instructionSig3Neg.matches(crashInfo2)

    # Crash info3 doesn't have register information, ensure we don't match any
    assert not instructionSig1.matches(crashInfo3)
    assert not instructionSig2.matches(crashInfo3)
    assert not instructionSig3.matches(crashInfo3)


def test_CrashSignatureStackFrameTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashSignature1 = {
        "symptoms": [{"type": "stackFrame", "functionName": "internalAppend"}]
    }
    crashSignature1Neg = {
        "symptoms": [{"type": "stackFrame", "functionName": "foobar"}]
    }

    crashSignature2 = {
        "symptoms": [
            {
                "type": "stackFrame",
                "functionName": "js::ion::MBasicBlock::setBackedge",
                "frameNumber": "<= 4",
            }
        ]
    }
    crashSignature2Neg = {
        "symptoms": [
            {
                "type": "stackFrame",
                "functionName": "js::ion::MBasicBlock::setBackedge",
                "frameNumber": "> 4",
            }
        ]
    }

    stackFrameSig1 = CrashSignature(json.dumps(crashSignature1))
    stackFrameSig1Neg = CrashSignature(json.dumps(crashSignature1Neg))

    stackFrameSig2 = CrashSignature(json.dumps(crashSignature2))
    stackFrameSig2Neg = CrashSignature(json.dumps(crashSignature2Neg))

    crashInfo1 = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_gdb_sample_1.txt").read_text().splitlines(),
    )

    assert isinstance(crashInfo1, GDBCrashInfo)

    assert stackFrameSig1.matches(crashInfo1)
    assert not stackFrameSig1Neg.matches(crashInfo1)

    assert stackFrameSig2.matches(crashInfo1)
    assert not stackFrameSig2Neg.matches(crashInfo1)


def test_CrashSignatureStackSizeTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashSignature1 = '{ "symptoms" : [ { "type" : "stackSize", "size" : 8 } ] }'
    crashSignature1Neg = '{ "symptoms" : [ { "type" : "stackSize", "size" : 9 } ] }'

    crashSignature2 = '{ "symptoms" : [ { "type" : "stackSize", "size" : "< 10" } ] }'
    crashSignature2Neg = (
        '{ "symptoms" : [ { "type" : "stackSize", "size" : "> 10" } ] }'
    )

    stackSizeSig1 = CrashSignature(crashSignature1)
    stackSizeSig1Neg = CrashSignature(crashSignature1Neg)

    stackSizeSig2 = CrashSignature(crashSignature2)
    stackSizeSig2Neg = CrashSignature(crashSignature2Neg)

    crashInfo1 = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        auxCrashData=(FIXTURE_PATH / "trace_gdb_sample_1.txt").read_text().splitlines(),
    )

    assert isinstance(crashInfo1, GDBCrashInfo)

    assert stackSizeSig1.matches(crashInfo1)
    assert not stackSizeSig1Neg.matches(crashInfo1)

    assert stackSizeSig2.matches(crashInfo1)
    assert not stackSizeSig2Neg.matches(crashInfo1)


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


def test_MinidumpParserTestCrash():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = MinidumpCrashInfo(
        [], (FIXTURE_PATH / "minidump-example.txt").read_text().splitlines(), config
    )

    assert len(crashInfo.backtrace) == 44
    assert crashInfo.backtrace[0] == "libc-2.15.so+0xe6b03"
    assert crashInfo.backtrace[5] == "libglib-2.0.so.0.3200.1+0x48123"
    assert crashInfo.backtrace[6] == "nsAppShell::ProcessNextNativeEvent"
    assert crashInfo.backtrace[7] == "nsBaseAppShell::DoProcessNextNativeEvent"

    assert crashInfo.crashAddress == 0x3E800006ACB


def test_MinidumpSelectorTest():
    config = ProgramConfiguration("test", "x86", "linux")

    crashData = (FIXTURE_PATH / "minidump-example.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x3E800006ACB


def test_MinidumpFromMacOSTest():
    config = ProgramConfiguration("test", "x86-64", "macosx")

    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_minidump_macos.txt").read_text().splitlines(),
    )
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "nsIFrame::UpdateOverflow"
    assert crashInfo.backtrace[1] == "mozilla::OverflowChangedTracker::Flush"
    assert crashInfo.backtrace[2] == "mozilla::RestyleManager::DoProcessPendingRestyles"
    assert crashInfo.backtrace[3] == "mozilla::PresShell::DoFlushPendingNotifications"
    assert crashInfo.crashAddress == 0


def test_AppleParserTestCrash():
    config = ProgramConfiguration("test", "x86-64", "macosx")

    crashInfo = AppleCrashInfo(
        [],
        [],
        config,
        (FIXTURE_PATH / "apple-crash-report-example.txt").read_text().splitlines(),
    )

    assert len(crashInfo.backtrace) == 9
    assert crashInfo.backtrace[0] == "js::jit::MacroAssembler::Pop"
    assert (
        crashInfo.backtrace[1]
        == "js::jit::ICGetPropCallNativeCompiler::generateStubCode"
    )
    assert crashInfo.backtrace[2] == "js::jit::ICStubCompiler::getStubCode"
    assert crashInfo.backtrace[3] == "js::jit::ICGetPropCallNativeCompiler::getStub"
    assert crashInfo.backtrace[4] == "js::jit::DoGetPropFallback"
    assert crashInfo.backtrace[5] == "??"
    assert crashInfo.backtrace[6] == "__cxa_finalize_ranges"
    assert crashInfo.backtrace[7] == "??"
    assert (
        crashInfo.backtrace[8]
        == "-[NSApplication _nextEventMatchingEventMask:untilDate:inMode:dequeue:]"
    )

    assert crashInfo.crashAddress == 0x00007FFF5F3FFF98


def test_AppleSelectorTest():
    config = ProgramConfiguration("test", "x86-64", "macosx")

    crashData = (
        (FIXTURE_PATH / "apple-crash-report-example.txt").read_text().splitlines()
    )

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00007FFF5F3FFF98


def test_AppleLionParserTestCrash():
    config = ProgramConfiguration("test", "x86-64", "macosx64")

    crashInfo = AppleCrashInfo(
        [],
        [],
        config,
        (FIXTURE_PATH / "apple-10-7-crash-report-example.txt").read_text().splitlines(),
    )

    assert len(crashInfo.backtrace) == 13
    assert crashInfo.backtrace[0] == "js::jit::LIRGenerator::visitNearbyInt"
    assert crashInfo.backtrace[1] == "js::jit::LIRGenerator::visitInstruction"
    assert crashInfo.backtrace[2] == "js::jit::LIRGenerator::visitBlock"
    assert crashInfo.backtrace[3] == "js::jit::LIRGenerator::generate"
    assert crashInfo.backtrace[4] == "js::jit::GenerateLIR"
    assert crashInfo.backtrace[5] == "js::jit::CompileBackEnd"
    assert crashInfo.backtrace[6] == (
        "_ZN2js3jitL7CompileEP9JSContextN2JS6Handle"
        "IP8JSScriptEEPNS0_13BaselineFrameEPhb"
    )
    assert crashInfo.backtrace[7] == "js::jit::IonCompileScriptForBaseline"
    assert crashInfo.backtrace[8] == "??"
    assert crashInfo.backtrace[9] == "??"
    assert crashInfo.backtrace[10] == "??"
    assert crashInfo.backtrace[11] == "??"
    assert (
        crashInfo.backtrace[12]
        == "_ZL13EnterBaselineP9JSContextRN2js3jit12EnterJitDataE"
    )

    assert crashInfo.crashAddress == 0x0000000000000000


def test_AppleLionSelectorTest():
    config = ProgramConfiguration("test", "x86-64", "macosx64")

    crashData = (
        (FIXTURE_PATH / "apple-10-7-crash-report-example.txt").read_text().splitlines()
    )

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x0000000000000000


# Test 1a is for Win7 with 32-bit js debug deterministic shell hitting the assertion
# failure:
#     js_dbg_32_dm_windows_62f79d676e0e!js::GetBytecodeLength
#     01814577 cc              int     3
def test_CDBParserTestCrash1a():
    config = ProgramConfiguration("test", "x86", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-1a-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 13
    assert crashInfo.backtrace[0] == "js::GetBytecodeLength"
    assert crashInfo.backtrace[1] == "js::coverage::LCovSource::writeScript"
    assert (
        crashInfo.backtrace[2]
        == "js::coverage::LCovCompartment::collectCodeCoverageInfo"
    )
    assert crashInfo.backtrace[3] == "GenerateLcovInfo"
    assert crashInfo.backtrace[4] == "js::GetCodeCoverageSummary"
    assert crashInfo.backtrace[5] == "GetLcovInfo"
    assert crashInfo.backtrace[6] == "js::CallJSNative"
    assert crashInfo.backtrace[7] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[8] == "InternalCall"
    assert crashInfo.backtrace[9] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[10] == "??"
    assert crashInfo.backtrace[11] == "EnterIon"
    assert crashInfo.backtrace[12] == "??"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["eax"] == 0x00000000
    assert crashInfo.registers["ebx"] == 0x00000001
    assert crashInfo.registers["ecx"] == 0x6A24705D
    assert crashInfo.registers["edx"] == 0x0034D9D4
    assert crashInfo.registers["esi"] == 0x0925B3EC
    assert crashInfo.registers["edi"] == 0x0925B3D1
    assert crashInfo.registers["eip"] == 0x01814577
    assert crashInfo.registers["esp"] == 0x0034EF5C
    assert crashInfo.registers["ebp"] == 0x0034EF5C

    assert crashInfo.crashAddress == 0x01814577


def test_CDBSelectorTest1a():
    config = ProgramConfiguration("test", "x86", "windows")

    crashData = (FIXTURE_PATH / "cdb-1a-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x01814577


# Test 1b is for Win10 with 32-bit js debug deterministic shell hitting the assertion
# failure:
#     js_dbg_32_dm_windows_62f79d676e0e!js::GetBytecodeLength+47
#     01344577 cc              int     3
def test_CDBParserTestCrash1b():
    config = ProgramConfiguration("test", "x86", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-1b-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 13
    assert crashInfo.backtrace[0] == "js::GetBytecodeLength"
    assert crashInfo.backtrace[1] == "js::coverage::LCovSource::writeScript"
    assert (
        crashInfo.backtrace[2]
        == "js::coverage::LCovCompartment::collectCodeCoverageInfo"
    )
    assert crashInfo.backtrace[3] == "GenerateLcovInfo"
    assert crashInfo.backtrace[4] == "js::GetCodeCoverageSummary"
    assert crashInfo.backtrace[5] == "GetLcovInfo"
    assert crashInfo.backtrace[6] == "js::CallJSNative"
    assert crashInfo.backtrace[7] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[8] == "InternalCall"
    assert crashInfo.backtrace[9] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[10] == "??"
    assert crashInfo.backtrace[11] == "EnterIon"
    assert crashInfo.backtrace[12] == "??"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["eax"] == 0x00000000
    assert crashInfo.registers["ebx"] == 0x00000001
    assert crashInfo.registers["ecx"] == 0x765E06EF
    assert crashInfo.registers["edx"] == 0x00000060
    assert crashInfo.registers["esi"] == 0x039604EC
    assert crashInfo.registers["edi"] == 0x039604D1
    assert crashInfo.registers["eip"] == 0x01344577
    assert crashInfo.registers["esp"] == 0x02B2EE1C
    assert crashInfo.registers["ebp"] == 0x02B2EE1C

    assert crashInfo.crashAddress == 0x01344577


def test_CDBSelectorTest1b():
    config = ProgramConfiguration("test", "x86", "windows")

    crashData = (FIXTURE_PATH / "cdb-1b-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x01344577


# Test 2a is for Win7 with 64-bit js debug deterministic shell hitting the assertion
# failure:
#     js_dbg_64_dm_windows_62f79d676e0e!js::GetBytecodeLength
#     00000001`40144e62 cc              int     3
def test_CDBParserTestCrash2a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-2a-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 25
    assert crashInfo.backtrace[0] == "js::GetBytecodeLength"
    assert crashInfo.backtrace[1] == "js::coverage::LCovSource::writeScript"
    assert (
        crashInfo.backtrace[2]
        == "js::coverage::LCovCompartment::collectCodeCoverageInfo"
    )
    assert crashInfo.backtrace[3] == "GenerateLcovInfo"
    assert crashInfo.backtrace[4] == "js::GetCodeCoverageSummary"
    assert crashInfo.backtrace[5] == "GetLcovInfo"
    assert crashInfo.backtrace[6] == "js::CallJSNative"
    assert crashInfo.backtrace[7] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[8] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[9] == "??"
    assert crashInfo.backtrace[10] == "??"
    assert crashInfo.backtrace[11] == "??"
    assert crashInfo.backtrace[12] == "??"
    assert crashInfo.backtrace[13] == "??"
    assert crashInfo.backtrace[14] == "??"
    assert crashInfo.backtrace[15] == "??"
    assert crashInfo.backtrace[16] == "??"
    assert crashInfo.backtrace[17] == "??"
    assert crashInfo.backtrace[18] == "??"
    assert crashInfo.backtrace[19] == "??"
    assert crashInfo.backtrace[20] == "??"
    assert crashInfo.backtrace[21] == "??"
    assert crashInfo.backtrace[22] == "??"
    assert crashInfo.backtrace[23] == "??"
    assert crashInfo.backtrace[24] == "??"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["rax"] == 0x0000000000000000
    assert crashInfo.registers["rbx"] == 0x0000000006C139AC
    assert crashInfo.registers["rcx"] == 0x000007FEF38241F0
    assert crashInfo.registers["rdx"] == 0x000007FEF38255F0
    assert crashInfo.registers["rsi"] == 0x0000000006C1399E
    assert crashInfo.registers["rdi"] == 0x0000000006CF2101
    assert crashInfo.registers["rip"] == 0x0000000140144E62
    assert crashInfo.registers["rsp"] == 0x000000000027E500
    assert crashInfo.registers["rbp"] == 0x0000000006CF2120
    assert crashInfo.registers["r8"] == 0x000000000027CE88
    assert crashInfo.registers["r9"] == 0x00000000020CC069
    assert crashInfo.registers["r10"] == 0x0000000000000000
    assert crashInfo.registers["r11"] == 0x000000000027E3F0
    assert crashInfo.registers["r12"] == 0x0000000006C0D088
    assert crashInfo.registers["r13"] == 0x0000000006C139AD
    assert crashInfo.registers["r14"] == 0x0000000000000000
    assert crashInfo.registers["r15"] == 0x0000000006C13991

    assert crashInfo.crashAddress == 0x0000000140144E62


def test_CDBSelectorTest2a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashData = (FIXTURE_PATH / "cdb-2a-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x0000000140144E62


# Test 2b is for Win10 with 64-bit js debug deterministic shell hitting the assertion
# failure:
#     js_dbg_64_dm_windows_62f79d676e0e!js::GetBytecodeLength+52
#     00007ff7`1e424e62 cc              int     3
def test_CDBParserTestCrash2b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-2b-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 25
    assert crashInfo.backtrace[0] == "js::GetBytecodeLength"
    assert crashInfo.backtrace[1] == "js::coverage::LCovSource::writeScript"
    assert (
        crashInfo.backtrace[2]
        == "js::coverage::LCovCompartment::collectCodeCoverageInfo"
    )
    assert crashInfo.backtrace[3] == "GenerateLcovInfo"
    assert crashInfo.backtrace[4] == "js::GetCodeCoverageSummary"
    assert crashInfo.backtrace[5] == "GetLcovInfo"
    assert crashInfo.backtrace[6] == "js::CallJSNative"
    assert crashInfo.backtrace[7] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[8] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[9] == "??"
    assert crashInfo.backtrace[10] == "??"
    assert crashInfo.backtrace[11] == "??"
    assert crashInfo.backtrace[12] == "??"
    assert crashInfo.backtrace[13] == "??"
    assert crashInfo.backtrace[14] == "??"
    assert crashInfo.backtrace[15] == "??"
    assert crashInfo.backtrace[16] == "??"
    assert crashInfo.backtrace[17] == "??"
    assert crashInfo.backtrace[18] == "??"
    assert crashInfo.backtrace[19] == "??"
    assert crashInfo.backtrace[20] == "??"
    assert crashInfo.backtrace[21] == "??"
    assert crashInfo.backtrace[22] == "??"
    assert crashInfo.backtrace[23] == "??"
    assert crashInfo.backtrace[24] == "??"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["rax"] == 0x0000000000000000
    assert crashInfo.registers["rbx"] == 0x0000024DBF40BAAC
    assert crashInfo.registers["rcx"] == 0x00000000FFFFFFFF
    assert crashInfo.registers["rdx"] == 0x0000000000000000
    assert crashInfo.registers["rsi"] == 0x0000024DBF40BA9E
    assert crashInfo.registers["rdi"] == 0x0000024DBF4F2201
    assert crashInfo.registers["rip"] == 0x00007FF71E424E62
    assert crashInfo.registers["rsp"] == 0x000000DE223FE3D0
    assert crashInfo.registers["rbp"] == 0x0000024DBF4F22E0
    assert crashInfo.registers["r8"] == 0x000000DE223FCD78
    assert crashInfo.registers["r9"] == 0x0000024DBEBE0735
    assert crashInfo.registers["r10"] == 0x0000000000000000
    assert crashInfo.registers["r11"] == 0x000000DE223FE240
    assert crashInfo.registers["r12"] == 0x0000024DBF414088
    assert crashInfo.registers["r13"] == 0x0000024DBF40BAAD
    assert crashInfo.registers["r14"] == 0x0000000000000000
    assert crashInfo.registers["r15"] == 0x0000024DBF40BA91

    assert crashInfo.crashAddress == 0x00007FF71E424E62


def test_CDBSelectorTest2b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashData = (FIXTURE_PATH / "cdb-2b-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00007FF71E424E62


# Test 3a is for Win7 with 32-bit js debug deterministic shell crashing:
#     js_dbg_32_dm_windows_62f79d676e0e!js::gc::TenuredCell::arena
#     00f36a63 8b00            mov     eax,dword ptr [eax]
def test_CDBParserTestCrash3a():
    config = ProgramConfiguration("test", "x86", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-3a-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 36
    assert crashInfo.backtrace[0] == "js::gc::TenuredCell::arena"
    assert crashInfo.backtrace[1] == "js::TenuringTracer::moveToTenured"
    assert crashInfo.backtrace[2] == "js::TenuringTracer::traverse"
    assert crashInfo.backtrace[3] == "js::DispatchTyped"
    assert crashInfo.backtrace[4] == "DispatchToTracer"
    assert crashInfo.backtrace[5] == "js::TraceRootRange"
    assert crashInfo.backtrace[6] == "js::jit::BaselineFrame::trace"
    assert crashInfo.backtrace[7] == "js::jit::MarkJitActivation"
    assert crashInfo.backtrace[8] == "js::jit::MarkJitActivations"
    assert crashInfo.backtrace[9] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert crashInfo.backtrace[10] == "js::Nursery::doCollection"
    assert crashInfo.backtrace[11] == "js::Nursery::collect"
    assert crashInfo.backtrace[12] == "js::gc::GCRuntime::minorGC"
    assert crashInfo.backtrace[13] == "js::gc::GCRuntime::runDebugGC"
    assert crashInfo.backtrace[14] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert crashInfo.backtrace[15] == "js::gc::GCRuntime::checkAllocatorState"
    assert crashInfo.backtrace[16] == "js::Allocate"
    assert crashInfo.backtrace[17] == "JSObject::create"
    assert crashInfo.backtrace[18] == "NewObject"
    assert crashInfo.backtrace[19] == "js::NewObjectWithGivenTaggedProto"
    assert crashInfo.backtrace[20] == "js::ProxyObject::New"
    assert crashInfo.backtrace[21] == "js::NewProxyObject"
    assert crashInfo.backtrace[22] == "js::Wrapper::New"
    assert crashInfo.backtrace[23] == "js::TransparentObjectWrapper"
    assert crashInfo.backtrace[24] == "JSCompartment::wrap"
    assert crashInfo.backtrace[25] == "JSCompartment::wrap"
    assert crashInfo.backtrace[26] == "js::CrossCompartmentWrapper::call"
    assert crashInfo.backtrace[27] == "js::Proxy::call"
    assert crashInfo.backtrace[28] == "js::proxy_Call"
    assert crashInfo.backtrace[29] == "js::CallJSNative"
    assert crashInfo.backtrace[30] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[31] == "InternalCall"
    assert crashInfo.backtrace[32] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[33] == "??"
    assert crashInfo.backtrace[34] == "EnterIon"
    assert crashInfo.backtrace[35] == "??"

    assert crashInfo.crashInstruction == "mov eax,dword ptr [eax]"
    assert crashInfo.registers["eax"] == 0x2B2FFFF0
    assert crashInfo.registers["ebx"] == 0x0041DE08
    assert crashInfo.registers["ecx"] == 0x2B2B2B2B
    assert crashInfo.registers["edx"] == 0x0A200310
    assert crashInfo.registers["esi"] == 0x0041DC68
    assert crashInfo.registers["edi"] == 0x0A200310
    assert crashInfo.registers["eip"] == 0x00F36A63
    assert crashInfo.registers["esp"] == 0x0041DC04
    assert crashInfo.registers["ebp"] == 0x0041DC2C

    assert crashInfo.crashAddress == 0x00F36A63


def test_CDBSelectorTest3a():
    config = ProgramConfiguration("test", "x86", "windows")

    crashData = (FIXTURE_PATH / "cdb-3a-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00F36A63


# Test 3b is for Win10 with 32-bit js debug deterministic shell crashing:
#     js_dbg_32_dm_windows_62f79d676e0e!js::gc::TenuredCell::arena+13
#     00ed6a63 8b00            mov     eax,dword ptr [eax]
def test_CDBParserTestCrash3b():
    config = ProgramConfiguration("test", "x86", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-3b-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 36
    assert crashInfo.backtrace[0] == "js::gc::TenuredCell::arena"
    assert crashInfo.backtrace[1] == "js::TenuringTracer::moveToTenured"
    assert crashInfo.backtrace[2] == "js::TenuringTracer::traverse"
    assert crashInfo.backtrace[3] == "js::DispatchTyped"
    assert crashInfo.backtrace[4] == "DispatchToTracer"
    assert crashInfo.backtrace[5] == "js::TraceRootRange"
    assert crashInfo.backtrace[6] == "js::jit::BaselineFrame::trace"
    assert crashInfo.backtrace[7] == "js::jit::MarkJitActivation"
    assert crashInfo.backtrace[8] == "js::jit::MarkJitActivations"
    assert crashInfo.backtrace[9] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert crashInfo.backtrace[10] == "js::Nursery::doCollection"
    assert crashInfo.backtrace[11] == "js::Nursery::collect"
    assert crashInfo.backtrace[12] == "js::gc::GCRuntime::minorGC"
    assert crashInfo.backtrace[13] == "js::gc::GCRuntime::runDebugGC"
    assert crashInfo.backtrace[14] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert crashInfo.backtrace[15] == "js::gc::GCRuntime::checkAllocatorState"
    assert crashInfo.backtrace[16] == "js::Allocate"
    assert crashInfo.backtrace[17] == "JSObject::create"
    assert crashInfo.backtrace[18] == "NewObject"
    assert crashInfo.backtrace[19] == "js::NewObjectWithGivenTaggedProto"
    assert crashInfo.backtrace[20] == "js::ProxyObject::New"
    assert crashInfo.backtrace[21] == "js::NewProxyObject"
    assert crashInfo.backtrace[22] == "js::Wrapper::New"
    assert crashInfo.backtrace[23] == "js::TransparentObjectWrapper"
    assert crashInfo.backtrace[24] == "JSCompartment::wrap"
    assert crashInfo.backtrace[25] == "JSCompartment::wrap"
    assert crashInfo.backtrace[26] == "js::CrossCompartmentWrapper::call"
    assert crashInfo.backtrace[27] == "js::Proxy::call"
    assert crashInfo.backtrace[28] == "js::proxy_Call"
    assert crashInfo.backtrace[29] == "js::CallJSNative"
    assert crashInfo.backtrace[30] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[31] == "InternalCall"
    assert crashInfo.backtrace[32] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[33] == "??"
    assert crashInfo.backtrace[34] == "EnterIon"
    assert crashInfo.backtrace[35] == "??"

    assert crashInfo.crashInstruction == "mov eax,dword ptr [eax]"
    assert crashInfo.registers["eax"] == 0x2B2FFFF0
    assert crashInfo.registers["ebx"] == 0x02B2DEB8
    assert crashInfo.registers["ecx"] == 0x2B2B2B2B
    assert crashInfo.registers["edx"] == 0x04200310
    assert crashInfo.registers["esi"] == 0x02B2DD18
    assert crashInfo.registers["edi"] == 0x04200310
    assert crashInfo.registers["eip"] == 0x00ED6A63
    assert crashInfo.registers["esp"] == 0x02B2DCB4
    assert crashInfo.registers["ebp"] == 0x02B2DCDC

    assert crashInfo.crashAddress == 0x00ED6A63


def test_CDBSelectorTest3b():
    config = ProgramConfiguration("test", "x86", "windows")

    crashData = (FIXTURE_PATH / "cdb-3b-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00ED6A63


# Test 4a is for Win7 with 32-bit js opt deterministic shell crashing:
#     js_32_dm_windows_62f79d676e0e!JSObject::allocKindForTenure
#     00d44c59 8b39            mov     edi,dword ptr [ecx]
def test_CDBParserTestCrash4a():
    config = ProgramConfiguration("test", "x86", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-4a-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 54
    assert crashInfo.backtrace[0] == "JSObject::allocKindForTenure"
    assert crashInfo.backtrace[1] == "js::TenuringTracer::moveToTenured"
    assert crashInfo.backtrace[2] == "js::TenuringTraversalFunctor"
    assert crashInfo.backtrace[3] == "js::DispatchTyped"
    assert crashInfo.backtrace[4] == "DispatchToTracer"
    assert crashInfo.backtrace[5] == "js::TraceRootRange"
    assert crashInfo.backtrace[6] == "js::jit::BaselineFrame::trace"
    assert crashInfo.backtrace[7] == "js::jit::MarkJitActivation"
    assert crashInfo.backtrace[8] == "js::jit::MarkJitActivations"
    assert crashInfo.backtrace[9] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert crashInfo.backtrace[10] == "js::Nursery::doCollection"
    assert crashInfo.backtrace[11] == "js::Nursery::collect"
    assert crashInfo.backtrace[12] == "js::gc::GCRuntime::minorGC"
    assert crashInfo.backtrace[13] == "js::gc::GCRuntime::runDebugGC"
    assert crashInfo.backtrace[14] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert crashInfo.backtrace[15] == "js::Allocate"
    assert crashInfo.backtrace[16] == "JSObject::create"
    assert crashInfo.backtrace[17] == "NewObject"
    assert crashInfo.backtrace[18] == "js::NewObjectWithGivenTaggedProto"
    assert crashInfo.backtrace[19] == "js::ProxyObject::New"
    assert crashInfo.backtrace[20] == "js::NewProxyObject"
    assert crashInfo.backtrace[21] == "js::Wrapper::New"
    assert crashInfo.backtrace[22] == "js::TransparentObjectWrapper"
    assert crashInfo.backtrace[23] == "JSCompartment::wrap"
    assert crashInfo.backtrace[24] == "JSCompartment::wrap"
    assert crashInfo.backtrace[25] == "js::CrossCompartmentWrapper::call"
    assert crashInfo.backtrace[26] == "js::Proxy::call"
    assert crashInfo.backtrace[27] == "js::proxy_Call"
    assert crashInfo.backtrace[28] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[29] == "InternalCall"
    assert crashInfo.backtrace[30] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[31] == "je_free"
    assert crashInfo.backtrace[32] == "js::jit::IonCannon"
    assert crashInfo.backtrace[33] == "js::RunScript"
    assert crashInfo.backtrace[34] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[35] == "InternalCall"
    assert crashInfo.backtrace[36] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[37] == "EnterBaseline"
    assert crashInfo.backtrace[38] == "js::jit::EnterBaselineAtBranch"
    assert crashInfo.backtrace[39] == "Interpret"
    assert crashInfo.backtrace[40] == "js::RunScript"
    assert crashInfo.backtrace[41] == "js::ExecuteKernel"
    assert crashInfo.backtrace[42] == "js::Execute"
    assert crashInfo.backtrace[43] == "ExecuteScript"
    assert crashInfo.backtrace[44] == "JS_ExecuteScript"
    assert crashInfo.backtrace[45] == "RunFile"
    assert crashInfo.backtrace[46] == "Process"
    assert crashInfo.backtrace[47] == "ProcessArgs"
    assert crashInfo.backtrace[48] == "Shell"
    assert crashInfo.backtrace[49] == "main"
    assert crashInfo.backtrace[50] == "__scrt_common_main_seh"
    assert crashInfo.backtrace[51] == "BaseThreadInitThunk"
    assert crashInfo.backtrace[52] == "RtlInitializeExceptionChain"
    assert crashInfo.backtrace[53] == "RtlInitializeExceptionChain"

    assert crashInfo.crashInstruction == "mov edi,dword ptr [ecx]"
    assert crashInfo.registers["eax"] == 0x09BFFF01
    assert crashInfo.registers["ebx"] == 0x002ADC18
    assert crashInfo.registers["ecx"] == 0x2B2B2B2B
    assert crashInfo.registers["edx"] == 0x002AE2F0
    assert crashInfo.registers["esi"] == 0x09B00310
    assert crashInfo.registers["edi"] == 0x09B00310
    assert crashInfo.registers["eip"] == 0x00D44C59
    assert crashInfo.registers["esp"] == 0x002ADA8C
    assert crashInfo.registers["ebp"] == 0x002ADC18

    assert crashInfo.crashAddress == 0x00D44C59


def test_CDBSelectorTest4a():
    config = ProgramConfiguration("test", "x86", "windows")

    crashData = (FIXTURE_PATH / "cdb-4a-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00D44C59


# Test 4b is for Win10 with 32-bit js opt deterministic shell crashing:
#     js_32_dm_windows_62f79d676e0e!JSObject::allocKindForTenure+9
#     00404c59 8b39            mov     edi,dword ptr [ecx]
def test_CDBParserTestCrash4b():
    config = ProgramConfiguration("test", "x86", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-4b-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 38
    assert crashInfo.backtrace[0] == "JSObject::allocKindForTenure"
    assert crashInfo.backtrace[1] == "js::TenuringTracer::moveToTenured"
    assert crashInfo.backtrace[2] == "js::TenuringTraversalFunctor"
    assert crashInfo.backtrace[3] == "js::DispatchTyped"
    assert crashInfo.backtrace[4] == "DispatchToTracer"
    assert crashInfo.backtrace[5] == "js::TraceRootRange"
    assert crashInfo.backtrace[6] == "js::jit::BaselineFrame::trace"
    assert crashInfo.backtrace[7] == "js::jit::MarkJitActivation"
    assert crashInfo.backtrace[8] == "js::jit::MarkJitActivations"
    assert crashInfo.backtrace[9] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert crashInfo.backtrace[10] == "js::Nursery::doCollection"
    assert crashInfo.backtrace[11] == "js::Nursery::collect"
    assert crashInfo.backtrace[12] == "js::gc::GCRuntime::minorGC"
    assert crashInfo.backtrace[13] == "js::gc::GCRuntime::runDebugGC"
    assert crashInfo.backtrace[14] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert crashInfo.backtrace[15] == "js::Allocate"
    assert crashInfo.backtrace[16] == "JSObject::create"
    assert crashInfo.backtrace[17] == "NewObject"
    assert crashInfo.backtrace[18] == "js::NewObjectWithGivenTaggedProto"
    assert crashInfo.backtrace[19] == "js::ProxyObject::New"
    assert crashInfo.backtrace[20] == "js::NewProxyObject"
    assert crashInfo.backtrace[21] == "js::Wrapper::New"
    assert crashInfo.backtrace[22] == "js::TransparentObjectWrapper"
    assert crashInfo.backtrace[23] == "JSCompartment::wrap"
    assert crashInfo.backtrace[24] == "JSCompartment::wrap"
    assert crashInfo.backtrace[25] == "js::CrossCompartmentWrapper::call"
    assert crashInfo.backtrace[26] == "js::Proxy::call"
    assert crashInfo.backtrace[27] == "js::proxy_Call"
    assert crashInfo.backtrace[28] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[29] == "InternalCall"
    assert crashInfo.backtrace[30] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[31] == "je_free"
    assert crashInfo.backtrace[32] == "js::jit::IonCannon"
    assert crashInfo.backtrace[33] == "js::RunScript"
    assert crashInfo.backtrace[34] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[35] == "InternalCall"
    assert crashInfo.backtrace[36] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[37] == "EnterBaseline"

    assert crashInfo.crashInstruction == "mov edi,dword ptr [ecx]"
    assert crashInfo.registers["eax"] == 0x02EFFF01
    assert crashInfo.registers["ebx"] == 0x016FDDB8
    assert crashInfo.registers["ecx"] == 0x2B2B2B2B
    assert crashInfo.registers["edx"] == 0x016FE490
    assert crashInfo.registers["esi"] == 0x02E00310
    assert crashInfo.registers["edi"] == 0x02E00310
    assert crashInfo.registers["eip"] == 0x00404C59
    assert crashInfo.registers["esp"] == 0x016FDC2C
    assert crashInfo.registers["ebp"] == 0x016FDDB8

    assert crashInfo.crashAddress == 0x00404C59


def test_CDBSelectorTest4b():
    config = ProgramConfiguration("test", "x86", "windows")

    crashData = (FIXTURE_PATH / "cdb-4b-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00404C59


# Test 5a is for Win7 with 64-bit js debug deterministic shell crashing:
#     js_dbg_64_dm_windows_62f79d676e0e!js::gc::IsInsideNursery
#     00000001`3f4975db 8b11            mov     edx,dword ptr [rcx]
def test_CDBParserTestCrash5a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-5a-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 34
    assert crashInfo.backtrace[0] == "js::gc::IsInsideNursery"
    assert crashInfo.backtrace[1] == "js::gc::TenuredCell::arena"
    assert crashInfo.backtrace[2] == "js::TenuringTracer::moveToTenured"
    assert crashInfo.backtrace[3] == "js::TenuringTracer::traverse"
    assert crashInfo.backtrace[4] == "js::DispatchTyped"
    assert crashInfo.backtrace[5] == "DispatchToTracer"
    assert crashInfo.backtrace[6] == "js::TraceRootRange"
    assert crashInfo.backtrace[7] == "js::jit::BaselineFrame::trace"
    assert crashInfo.backtrace[8] == "js::jit::MarkJitActivation"
    assert crashInfo.backtrace[9] == "js::jit::MarkJitActivations"
    assert crashInfo.backtrace[10] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert crashInfo.backtrace[11] == "js::Nursery::doCollection"
    assert crashInfo.backtrace[12] == "js::Nursery::collect"
    assert crashInfo.backtrace[13] == "js::gc::GCRuntime::minorGC"
    assert crashInfo.backtrace[14] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert crashInfo.backtrace[15] == "js::gc::GCRuntime::checkAllocatorState"
    assert crashInfo.backtrace[16] == "js::Allocate"
    assert crashInfo.backtrace[17] == "JSObject::create"
    assert crashInfo.backtrace[18] == "NewObject"
    assert crashInfo.backtrace[19] == "js::NewObjectWithGivenTaggedProto"
    assert crashInfo.backtrace[20] == "js::ProxyObject::New"
    assert crashInfo.backtrace[21] == "js::NewProxyObject"
    assert crashInfo.backtrace[22] == "js::Wrapper::New"
    assert crashInfo.backtrace[23] == "js::TransparentObjectWrapper"
    assert crashInfo.backtrace[24] == "JSCompartment::wrap"
    assert crashInfo.backtrace[25] == "JSCompartment::wrap"
    assert crashInfo.backtrace[26] == "js::CrossCompartmentWrapper::call"
    assert crashInfo.backtrace[27] == "js::Proxy::call"
    assert crashInfo.backtrace[28] == "js::proxy_Call"
    assert crashInfo.backtrace[29] == "js::CallJSNative"
    assert crashInfo.backtrace[30] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[31] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[32] == "??"
    assert crashInfo.backtrace[33] == "??"

    assert crashInfo.crashInstruction == "mov edx,dword ptr [rcx]"
    assert crashInfo.registers["rax"] == 0x0000000000000001
    assert crashInfo.registers["rbx"] == 0xFFFE2B2B2B2B2B2B
    assert crashInfo.registers["rcx"] == 0xFFFE2B2B2B2FFFE8
    assert crashInfo.registers["rdx"] == 0x0000000000000001
    assert crashInfo.registers["rsi"] == 0x000000000040C078
    assert crashInfo.registers["rdi"] == 0x0000000006A00420
    assert crashInfo.registers["rip"] == 0x000000013F4975DB
    assert crashInfo.registers["rsp"] == 0x000000000040BC40
    assert crashInfo.registers["rbp"] == 0x0000000000000006
    assert crashInfo.registers["r8"] == 0x0000000006633200
    assert crashInfo.registers["r9"] == 0x000000014079B1A0
    assert crashInfo.registers["r10"] == 0x0000000000000031
    assert crashInfo.registers["r11"] == 0x0000000000000033
    assert crashInfo.registers["r12"] == 0xFFFA7FFFFFFFFFFF
    assert crashInfo.registers["r13"] == 0xFFFC000000000000
    assert crashInfo.registers["r14"] == 0x000000000040C078
    assert crashInfo.registers["r15"] == 0x000000014079B1A0

    assert crashInfo.crashAddress == 0x000000013F4975DB


def test_CDBSelectorTest5a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashData = (FIXTURE_PATH / "cdb-5a-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x000000013F4975DB


# Test 5b is for Win10 with 64-bit js debug deterministic shell crashing:
#     js_dbg_64_dm_windows_62f79d676e0e!js::gc::IsInsideNursery+1b
#     00007ff7`1dcf75db 8b11            mov     edx,dword ptr [rcx]
def test_CDBParserTestCrash5b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-5b-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 34
    assert crashInfo.backtrace[0] == "js::gc::IsInsideNursery"
    assert crashInfo.backtrace[1] == "js::gc::TenuredCell::arena"
    assert crashInfo.backtrace[2] == "js::TenuringTracer::moveToTenured"
    assert crashInfo.backtrace[3] == "js::TenuringTracer::traverse"
    assert crashInfo.backtrace[4] == "js::DispatchTyped"
    assert crashInfo.backtrace[5] == "DispatchToTracer"
    assert crashInfo.backtrace[6] == "js::TraceRootRange"
    assert crashInfo.backtrace[7] == "js::jit::BaselineFrame::trace"
    assert crashInfo.backtrace[8] == "js::jit::MarkJitActivation"
    assert crashInfo.backtrace[9] == "js::jit::MarkJitActivations"
    assert crashInfo.backtrace[10] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert crashInfo.backtrace[11] == "js::Nursery::doCollection"
    assert crashInfo.backtrace[12] == "js::Nursery::collect"
    assert crashInfo.backtrace[13] == "js::gc::GCRuntime::minorGC"
    assert crashInfo.backtrace[14] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert crashInfo.backtrace[15] == "js::gc::GCRuntime::checkAllocatorState"
    assert crashInfo.backtrace[16] == "js::Allocate"
    assert crashInfo.backtrace[17] == "JSObject::create"
    assert crashInfo.backtrace[18] == "NewObject"
    assert crashInfo.backtrace[19] == "js::NewObjectWithGivenTaggedProto"
    assert crashInfo.backtrace[20] == "js::ProxyObject::New"
    assert crashInfo.backtrace[21] == "js::NewProxyObject"
    assert crashInfo.backtrace[22] == "js::Wrapper::New"
    assert crashInfo.backtrace[23] == "js::TransparentObjectWrapper"
    assert crashInfo.backtrace[24] == "JSCompartment::wrap"
    assert crashInfo.backtrace[25] == "JSCompartment::wrap"
    assert crashInfo.backtrace[26] == "js::CrossCompartmentWrapper::call"
    assert crashInfo.backtrace[27] == "js::Proxy::call"
    assert crashInfo.backtrace[28] == "js::proxy_Call"
    assert crashInfo.backtrace[29] == "js::CallJSNative"
    assert crashInfo.backtrace[30] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[31] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[32] == "??"
    assert crashInfo.backtrace[33] == "??"

    assert crashInfo.crashInstruction == "mov edx,dword ptr [rcx]"
    assert crashInfo.registers["rax"] == 0x0000000000000001
    assert crashInfo.registers["rbx"] == 0xFFFE2B2B2B2B2B2B
    assert crashInfo.registers["rcx"] == 0xFFFE2B2B2B2FFFE8
    assert crashInfo.registers["rdx"] == 0x0000000000000001
    assert crashInfo.registers["rsi"] == 0x000000C4A47FC528
    assert crashInfo.registers["rdi"] == 0x0000021699700420
    assert crashInfo.registers["rip"] == 0x00007FF71DCF75DB
    assert crashInfo.registers["rsp"] == 0x000000C4A47FC0F0
    assert crashInfo.registers["rbp"] == 0x0000000000000006
    assert crashInfo.registers["r8"] == 0x0000021699633200
    assert crashInfo.registers["r9"] == 0x00007FF71EFFA590
    assert crashInfo.registers["r10"] == 0x0000000000000031
    assert crashInfo.registers["r11"] == 0x0000000000000033
    assert crashInfo.registers["r12"] == 0xFFFA7FFFFFFFFFFF
    assert crashInfo.registers["r13"] == 0xFFFC000000000000
    assert crashInfo.registers["r14"] == 0x000000C4A47FC528
    assert crashInfo.registers["r15"] == 0x00007FF71EFFA590

    assert crashInfo.crashAddress == 0x00007FF71DCF75DB


def test_CDBSelectorTest5b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashData = (FIXTURE_PATH / "cdb-5b-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00007FF71DCF75DB


# Test 6a is for Win7 with 64-bit js opt deterministic shell crashing:
#     js_64_dm_windows_62f79d676e0e!JSObject::allocKindForTenure
#     00000001`3f869ff3 4c8b01          mov     r8,qword ptr [rcx]
def test_CDBParserTestCrash6a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-6a-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 58
    assert crashInfo.backtrace[0] == "JSObject::allocKindForTenure"
    assert crashInfo.backtrace[1] == "js::TenuringTracer::moveToTenured"
    assert crashInfo.backtrace[2] == "js::DispatchTyped"
    assert crashInfo.backtrace[3] == "js::TraceRootRange"
    assert crashInfo.backtrace[4] == "js::jit::BaselineFrame::trace"
    assert crashInfo.backtrace[5] == "js::jit::MarkJitActivation"
    assert crashInfo.backtrace[6] == "js::jit::MarkJitActivations"
    assert crashInfo.backtrace[7] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert crashInfo.backtrace[8] == "js::Nursery::doCollection"
    assert crashInfo.backtrace[9] == "js::Nursery::collect"
    assert crashInfo.backtrace[10] == "js::gc::GCRuntime::minorGC"
    assert crashInfo.backtrace[11] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert crashInfo.backtrace[12] == "js::Allocate"
    assert crashInfo.backtrace[13] == "JSObject::create"
    assert crashInfo.backtrace[14] == "NewObject"
    assert crashInfo.backtrace[15] == "js::NewObjectWithGivenTaggedProto"
    assert crashInfo.backtrace[16] == "js::ProxyObject::New"
    assert crashInfo.backtrace[17] == "js::NewProxyObject"
    assert crashInfo.backtrace[18] == "js::TransparentObjectWrapper"
    assert crashInfo.backtrace[19] == "JSCompartment::wrap"
    assert crashInfo.backtrace[20] == "JSCompartment::wrap"
    assert crashInfo.backtrace[21] == "js::CrossCompartmentWrapper::call"
    assert crashInfo.backtrace[22] == "js::Proxy::call"
    assert crashInfo.backtrace[23] == "js::proxy_Call"
    assert crashInfo.backtrace[24] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[25] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[26] == "??"
    assert crashInfo.backtrace[27] == "??"
    assert crashInfo.backtrace[28] == "??"
    assert crashInfo.backtrace[29] == "??"
    assert crashInfo.backtrace[30] == "??"
    assert crashInfo.backtrace[31] == "??"
    assert crashInfo.backtrace[32] == "??"
    assert crashInfo.backtrace[33] == "??"
    assert crashInfo.backtrace[34] == "??"
    assert crashInfo.backtrace[35] == "??"
    assert crashInfo.backtrace[36] == "??"
    assert crashInfo.backtrace[37] == "??"
    assert crashInfo.backtrace[38] == "??"
    assert crashInfo.backtrace[39] == "??"
    assert crashInfo.backtrace[40] == "??"
    assert crashInfo.backtrace[41] == "??"
    assert crashInfo.backtrace[42] == "??"
    assert crashInfo.backtrace[43] == "??"
    assert crashInfo.backtrace[44] == "??"
    assert crashInfo.backtrace[45] == "??"
    assert crashInfo.backtrace[46] == "??"
    assert crashInfo.backtrace[47] == "??"
    assert crashInfo.backtrace[48] == "??"
    assert crashInfo.backtrace[49] == "??"
    assert crashInfo.backtrace[50] == "??"
    assert crashInfo.backtrace[51] == "??"
    assert crashInfo.backtrace[52] == "??"
    assert crashInfo.backtrace[53] == "??"
    assert crashInfo.backtrace[54] == "??"
    assert crashInfo.backtrace[55] == "??"
    assert crashInfo.backtrace[56] == "??"
    assert crashInfo.backtrace[57] == "??"

    assert crashInfo.crashInstruction == "mov r8,qword ptr [rcx]"
    assert crashInfo.registers["rax"] == 0x000000013FCFEEF0
    assert crashInfo.registers["rbx"] == 0x0000000008D00420
    assert crashInfo.registers["rcx"] == 0x2B2B2B2B2B2B2B2B
    assert crashInfo.registers["rdx"] == 0x000000000681B940
    assert crashInfo.registers["rsi"] == 0x000000000034C7B0
    assert crashInfo.registers["rdi"] == 0x0000000008D00420
    assert crashInfo.registers["rip"] == 0x000000013F869FF3
    assert crashInfo.registers["rsp"] == 0x000000000034C4B0
    assert crashInfo.registers["rbp"] == 0xFFFE000000000000
    assert crashInfo.registers["r8"] == 0x000000000034C5B0
    assert crashInfo.registers["r9"] == 0x000000000001FFFC
    assert crashInfo.registers["r10"] == 0x000000000000061D
    assert crashInfo.registers["r11"] == 0x000000000685A000
    assert crashInfo.registers["r12"] == 0x000000013FD23A98
    assert crashInfo.registers["r13"] == 0xFFFA7FFFFFFFFFFF
    assert crashInfo.registers["r14"] == 0x000000000034D550
    assert crashInfo.registers["r15"] == 0x0000000000000003

    assert crashInfo.crashAddress == 0x000000013F869FF3


def test_CDBSelectorTest6a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashData = (FIXTURE_PATH / "cdb-6a-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x000000013F869FF3


# Test 6b is for Win10 with 64-bit js opt deterministic shell crashing:
#     js_64_dm_windows_62f79d676e0e!JSObject::allocKindForTenure+13
#     00007ff7`4d469ff3 4c8b01          mov     r8,qword ptr [rcx]
def test_CDBParserTestCrash6b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-6b-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 58
    assert crashInfo.backtrace[0] == "JSObject::allocKindForTenure"
    assert crashInfo.backtrace[1] == "js::TenuringTracer::moveToTenured"
    assert crashInfo.backtrace[2] == "js::DispatchTyped"
    assert crashInfo.backtrace[3] == "js::TraceRootRange"
    assert crashInfo.backtrace[4] == "js::jit::BaselineFrame::trace"
    assert crashInfo.backtrace[5] == "js::jit::MarkJitActivation"
    assert crashInfo.backtrace[6] == "js::jit::MarkJitActivations"
    assert crashInfo.backtrace[7] == "js::gc::GCRuntime::traceRuntimeCommon"
    assert crashInfo.backtrace[8] == "js::Nursery::doCollection"
    assert crashInfo.backtrace[9] == "js::Nursery::collect"
    assert crashInfo.backtrace[10] == "js::gc::GCRuntime::minorGC"
    assert crashInfo.backtrace[11] == "js::gc::GCRuntime::gcIfNeededPerAllocation"
    assert crashInfo.backtrace[12] == "js::Allocate"
    assert crashInfo.backtrace[13] == "JSObject::create"
    assert crashInfo.backtrace[14] == "NewObject"
    assert crashInfo.backtrace[15] == "js::NewObjectWithGivenTaggedProto"
    assert crashInfo.backtrace[16] == "js::ProxyObject::New"
    assert crashInfo.backtrace[17] == "js::NewProxyObject"
    assert crashInfo.backtrace[18] == "js::TransparentObjectWrapper"
    assert crashInfo.backtrace[19] == "JSCompartment::wrap"
    assert crashInfo.backtrace[20] == "JSCompartment::wrap"
    assert crashInfo.backtrace[21] == "js::CrossCompartmentWrapper::call"
    assert crashInfo.backtrace[22] == "js::Proxy::call"
    assert crashInfo.backtrace[23] == "js::proxy_Call"
    assert crashInfo.backtrace[24] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[25] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[26] == "??"
    assert crashInfo.backtrace[27] == "??"
    assert crashInfo.backtrace[28] == "??"
    assert crashInfo.backtrace[29] == "??"
    assert crashInfo.backtrace[30] == "??"
    assert crashInfo.backtrace[31] == "??"
    assert crashInfo.backtrace[32] == "??"
    assert crashInfo.backtrace[33] == "??"
    assert crashInfo.backtrace[34] == "??"
    assert crashInfo.backtrace[35] == "??"
    assert crashInfo.backtrace[36] == "??"
    assert crashInfo.backtrace[37] == "??"
    assert crashInfo.backtrace[38] == "??"
    assert crashInfo.backtrace[39] == "??"
    assert crashInfo.backtrace[40] == "??"
    assert crashInfo.backtrace[41] == "??"
    assert crashInfo.backtrace[42] == "??"
    assert crashInfo.backtrace[43] == "??"
    assert crashInfo.backtrace[44] == "??"
    assert crashInfo.backtrace[45] == "??"
    assert crashInfo.backtrace[46] == "??"
    assert crashInfo.backtrace[47] == "??"
    assert crashInfo.backtrace[48] == "??"
    assert crashInfo.backtrace[49] == "??"
    assert crashInfo.backtrace[50] == "??"
    assert crashInfo.backtrace[51] == "??"
    assert crashInfo.backtrace[52] == "??"
    assert crashInfo.backtrace[53] == "??"
    assert crashInfo.backtrace[54] == "??"
    assert crashInfo.backtrace[55] == "??"
    assert crashInfo.backtrace[56] == "??"
    assert crashInfo.backtrace[57] == "??"

    assert crashInfo.crashInstruction == "mov r8,qword ptr [rcx]"
    assert crashInfo.registers["rax"] == 0x00007FF74D8FEE30
    assert crashInfo.registers["rbx"] == 0x00000285EF400420
    assert crashInfo.registers["rcx"] == 0x2B2B2B2B2B2B2B2B
    assert crashInfo.registers["rdx"] == 0x00000285EF21B940
    assert crashInfo.registers["rsi"] == 0x000000E87FBFC340
    assert crashInfo.registers["rdi"] == 0x00000285EF400420
    assert crashInfo.registers["rip"] == 0x00007FF74D469FF3
    assert crashInfo.registers["rsp"] == 0x000000E87FBFC040
    assert crashInfo.registers["rbp"] == 0xFFFE000000000000
    assert crashInfo.registers["r8"] == 0x00000E87FBFC140
    assert crashInfo.registers["r9"] == 0x00000000001FFFC
    assert crashInfo.registers["r10"] == 0x0000000000000649
    assert crashInfo.registers["r11"] == 0x00000285EF25A000
    assert crashInfo.registers["r12"] == 0x00007FF74D9239A0
    assert crashInfo.registers["r13"] == 0xFFFA7FFFFFFFFFFF
    assert crashInfo.registers["r14"] == 0x000000E87FBFD0E0
    assert crashInfo.registers["r15"] == 0x0000000000000003

    assert crashInfo.crashAddress == 0x00007FF74D469FF3


def test_CDBSelectorTest6b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashData = (FIXTURE_PATH / "cdb-6b-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00007FF74D469FF3


# Test 7 is for Windows Server 2012 R2 with 32-bit js debug deterministic shell:
#     +205
#     25d80b01 cc              int     3
def test_CDBParserTestCrash7():
    config = ProgramConfiguration("test", "x86", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-7c-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 46
    assert crashInfo.backtrace[0] == "??"
    assert crashInfo.backtrace[1] == "arena_run_dalloc"
    assert crashInfo.backtrace[2] == "EnterIon"
    assert crashInfo.backtrace[3] == "js::jit::IonCannon"
    assert crashInfo.backtrace[4] == "js::RunScript"
    assert crashInfo.backtrace[5] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[6] == "InternalCall"
    assert crashInfo.backtrace[7] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[8] == "??"
    assert crashInfo.backtrace[9] == "je_free"
    assert crashInfo.backtrace[10] == "EnterIon"
    assert crashInfo.backtrace[11] == "js::jit::IonCannon"
    assert crashInfo.backtrace[12] == "js::RunScript"
    assert crashInfo.backtrace[13] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[14] == "InternalCall"
    assert crashInfo.backtrace[15] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[16] == "EnterIon"
    assert crashInfo.backtrace[17] == "js::jit::IonCannon"
    assert crashInfo.backtrace[18] == "js::RunScript"
    assert crashInfo.backtrace[19] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[20] == "InternalCall"
    assert crashInfo.backtrace[21] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[22] == "??"
    assert crashInfo.backtrace[23] == "??"
    assert crashInfo.backtrace[24] == "EnterIon"
    assert crashInfo.backtrace[25] == "js::jit::IonCannon"
    assert crashInfo.backtrace[26] == "js::RunScript"
    assert crashInfo.backtrace[27] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[28] == "InternalCall"
    assert crashInfo.backtrace[29] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[30] == "EnterBaseline"
    assert crashInfo.backtrace[31] == "js::jit::EnterBaselineMethod"
    assert crashInfo.backtrace[32] == "js::RunScript"
    assert crashInfo.backtrace[33] == "js::ExecuteKernel"
    assert crashInfo.backtrace[34] == "js::Execute"
    assert crashInfo.backtrace[35] == "ExecuteScript"
    assert crashInfo.backtrace[36] == "JS_ExecuteScript"
    assert crashInfo.backtrace[37] == "RunFile"
    assert crashInfo.backtrace[38] == "Process"
    assert crashInfo.backtrace[39] == "ProcessArgs"
    assert crashInfo.backtrace[40] == "Shell"
    assert crashInfo.backtrace[41] == "main"
    assert crashInfo.backtrace[42] == "__scrt_common_main_seh"
    assert crashInfo.backtrace[43] == "kernel32"
    assert crashInfo.backtrace[44] == "ntdll"
    assert crashInfo.backtrace[45] == "ntdll"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["eax"] == 0x00C8A948
    assert crashInfo.registers["ebx"] == 0x0053E32C
    assert crashInfo.registers["ecx"] == 0x6802052B
    assert crashInfo.registers["edx"] == 0x00000000
    assert crashInfo.registers["esi"] == 0x25D8094B
    assert crashInfo.registers["edi"] == 0x0053E370
    assert crashInfo.registers["eip"] == 0x25D80B01
    assert crashInfo.registers["esp"] == 0x0053E370
    assert crashInfo.registers["ebp"] == 0xFFE00000

    assert crashInfo.crashAddress == 0x25D80B01


def test_CDBSelectorTest7():
    config = ProgramConfiguration("test", "x86", "windows")

    crashData = (FIXTURE_PATH / "cdb-7c-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x25D80B01


# Test 8 is for Windows Server 2012 R2 with 32-bit js debug profiling deterministic
# shell:
#     js_dbg_32_prof_dm_windows_42c95d88aaaa!js::jit::Range::upper+3d [
#         c:\users\administrator\trees\mozilla-central\js\src\jit\rangeanalysis.h @ 578]
#     0142865d cc              int     3
def test_CDBParserTestCrash8():
    config = ProgramConfiguration("test", "x86", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-8c-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 1
    assert crashInfo.backtrace[0] == "??"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["eax"] == 0x00000000
    assert crashInfo.registers["ebx"] == 0x00000000
    assert crashInfo.registers["ecx"] == 0x73F1705D
    assert crashInfo.registers["edx"] == 0x00EA9210
    assert crashInfo.registers["esi"] == 0x00000383
    assert crashInfo.registers["edi"] == 0x0A03D110
    assert crashInfo.registers["eip"] == 0x0142865D
    assert crashInfo.registers["esp"] == 0x00EAA780
    assert crashInfo.registers["ebp"] == 0x00EAA7EC

    assert crashInfo.crashAddress == 0x0142865D


def test_CDBSelectorTest8():
    config = ProgramConfiguration("test", "x86", "windows")

    crashData = (FIXTURE_PATH / "cdb-8c-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x0142865D


# Test 9 is for Windows Server 2012 R2 with 32-bit js opt profiling shell:
#     +1d8
#     0f2bb4f3 cc              int     3
def test_CDBParserTestCrash9():
    config = ProgramConfiguration("test", "x86", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-9c-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 44
    assert crashInfo.backtrace[0] == "??"
    assert crashInfo.backtrace[1] == "??"
    assert crashInfo.backtrace[2] == "js::AddTypePropertyId"
    assert crashInfo.backtrace[3] == "js::jit::EnterBaselineMethod"
    assert crashInfo.backtrace[4] == "??"
    assert crashInfo.backtrace[5] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[6] == "InternalCall"
    assert crashInfo.backtrace[7] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[8] == "??"
    assert crashInfo.backtrace[9] == "js::Activation::Activation"
    assert crashInfo.backtrace[10] == "EnterBaseline"
    assert crashInfo.backtrace[11] == "??"
    assert crashInfo.backtrace[12] == "js::RunScript"
    assert crashInfo.backtrace[13] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[14] == "InternalCall"
    assert crashInfo.backtrace[15] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[16] == "??"
    assert crashInfo.backtrace[17] == "??"
    assert crashInfo.backtrace[18] == "js::Activation::Activation"
    assert crashInfo.backtrace[19] == "EnterBaseline"
    assert crashInfo.backtrace[20] == "??"
    assert crashInfo.backtrace[21] == "js::RunScript"
    assert crashInfo.backtrace[22] == "js::InternalCallOrConstruct"
    assert crashInfo.backtrace[23] == "InternalCall"
    assert crashInfo.backtrace[24] == "js::jit::DoCallFallback"
    assert crashInfo.backtrace[25] == "??"
    assert crashInfo.backtrace[26] == "EnterBaseline"
    assert crashInfo.backtrace[27] == "??"
    assert crashInfo.backtrace[28] == "EnterBaseline"
    assert crashInfo.backtrace[29] == "js::jit::EnterBaselineMethod"
    assert crashInfo.backtrace[30] == "js::RunScript"
    assert crashInfo.backtrace[31] == "js::ExecuteKernel"
    assert crashInfo.backtrace[32] == "js::Execute"
    assert crashInfo.backtrace[33] == "ExecuteScript"
    assert crashInfo.backtrace[34] == "JS_ExecuteScript"
    assert crashInfo.backtrace[35] == "RunFile"
    assert crashInfo.backtrace[36] == "Process"
    assert crashInfo.backtrace[37] == "ProcessArgs"
    assert crashInfo.backtrace[38] == "Shell"
    assert crashInfo.backtrace[39] == "main"
    assert crashInfo.backtrace[40] == "__scrt_common_main_seh"
    assert crashInfo.backtrace[41] == "kernel32"
    assert crashInfo.backtrace[42] == "ntdll"
    assert crashInfo.backtrace[43] == "ntdll"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["eax"] == 0x00000020
    assert crashInfo.registers["ebx"] == 0x00B0EA18
    assert crashInfo.registers["ecx"] == 0x00000400
    assert crashInfo.registers["edx"] == 0x73E74F80
    assert crashInfo.registers["esi"] == 0xFFFFFF8C
    assert crashInfo.registers["edi"] == 0x00B0EA00
    assert crashInfo.registers["eip"] == 0x0F2BB4F3
    assert crashInfo.registers["esp"] == 0x00B0EA00
    assert crashInfo.registers["ebp"] == 0x00B0EAB0

    assert crashInfo.crashAddress == 0x0F2BB4F3


def test_CDBSelectorTest9():
    config = ProgramConfiguration("test", "x86", "windows")

    crashData = (FIXTURE_PATH / "cdb-9c-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x0F2BB4F3


# Test 10 is for Windows Server 2012 R2 with 32-bit js opt profiling shell:
#     +82
#     1c2fbbb0 cc              int     3
def test_CDBParserTestCrash10():
    config = ProgramConfiguration("test", "x86", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-10c-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 5
    assert crashInfo.backtrace[0] == "??"
    assert crashInfo.backtrace[1] == "js::jit::PrepareOsrTempData"
    assert crashInfo.backtrace[2] == "??"
    assert crashInfo.backtrace[3] == "js::AddTypePropertyId"
    assert crashInfo.backtrace[4] == "JSObject::makeLazyGroup"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["eax"] == 0x06FDA948
    assert crashInfo.registers["ebx"] == 0x020DE8DC
    assert crashInfo.registers["ecx"] == 0x5F7B6461
    assert crashInfo.registers["edx"] == 0x00000000
    assert crashInfo.registers["esi"] == 0x1C2FBAAB
    assert crashInfo.registers["edi"] == 0x020DE910
    assert crashInfo.registers["eip"] == 0x1C2FBBB0
    assert crashInfo.registers["esp"] == 0x020DE910
    assert crashInfo.registers["ebp"] == 0x00000018

    assert crashInfo.crashAddress == 0x1C2FBBB0


def test_CDBSelectorTest10():
    config = ProgramConfiguration("test", "x86", "windows")

    crashData = (FIXTURE_PATH / "cdb-10c-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x1C2FBBB0


# Test 11 is for Windows Server 2012 R2 with 32-bit js debug profiling deterministic
# shell:
#     js_dbg_32_prof_dm_windows_42c95d88aaaa!js::jit::Range::upper+3d [
#         c:\users\administrator\trees\mozilla-central\js\src\jit\rangeanalysis.h @ 578]
#     0156865d cc              int     3
def test_CDBParserTestCrash11():
    config = ProgramConfiguration("test", "x86", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-11c-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 1
    assert crashInfo.backtrace[0] == "??"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["eax"] == 0x00000000
    assert crashInfo.registers["ebx"] == 0x00000000
    assert crashInfo.registers["ecx"] == 0x738F705D
    assert crashInfo.registers["edx"] == 0x00E7B0E0
    assert crashInfo.registers["esi"] == 0x00000383
    assert crashInfo.registers["edi"] == 0x0BA37110
    assert crashInfo.registers["eip"] == 0x0156865D
    assert crashInfo.registers["esp"] == 0x00E7C650
    assert crashInfo.registers["ebp"] == 0x00E7C6BC

    assert crashInfo.crashAddress == 0x0156865D


def test_CDBSelectorTest11():
    config = ProgramConfiguration("test", "x86", "windows")

    crashData = (FIXTURE_PATH / "cdb-11c-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x0156865D


# Test 12 is for Windows Server 2012 R2 with 32-bit js opt profiling deterministic shell
#     +1d8
#     1fa0b7f8 cc              int     3
def test_CDBParserTestCrash12():
    config = ProgramConfiguration("test", "x86", "windows")

    crashInfo = CDBCrashInfo(
        [], [], config, (FIXTURE_PATH / "cdb-12c-crashlog.txt").read_text().splitlines()
    )

    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "??"
    assert crashInfo.backtrace[1] == "??"
    assert crashInfo.backtrace[2] == "js::AddTypePropertyId"
    assert crashInfo.backtrace[3] == "JSObject::makeLazyGroup"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["eax"] == 0x00000020
    assert crashInfo.registers["ebx"] == 0x0044EA78
    assert crashInfo.registers["ecx"] == 0x00000000
    assert crashInfo.registers["edx"] == 0x73BF4F80
    assert crashInfo.registers["esi"] == 0xFFFFFF8C
    assert crashInfo.registers["edi"] == 0x0044EA50
    assert crashInfo.registers["eip"] == 0x1FA0B7F8
    assert crashInfo.registers["esp"] == 0x0044EA50
    assert crashInfo.registers["ebp"] == 0x0044EB00

    assert crashInfo.crashAddress == 0x1FA0B7F8


def test_CDBSelectorTest12():
    config = ProgramConfiguration("test", "x86", "windows")

    crashData = (FIXTURE_PATH / "cdb-12c-crashlog.txt").read_text().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x1FA0B7F8


def test_UBSanParserTestCrash1():
    config = ProgramConfiguration("test", "x86", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_ubsan_signed_int_overflow.txt").read_text().splitlines(),
    )
    assert crashInfo.createShortSignature() == (
        "UndefinedBehaviorSanitizer: "
        "codec/decoder/core/inc/dec_golomb.h:182:37: "
        "runtime error: signed integer overflow: -2147483648 - "
        "1 cannot be represented in type 'int'"
    )
    assert len(crashInfo.backtrace) == 12
    assert crashInfo.backtrace[0] == "WelsDec::BsGetUe"
    assert crashInfo.backtrace[9] == "_start"
    assert crashInfo.backtrace[11] == "Lex< >"
    assert crashInfo.crashAddress is None


def test_UBSanParserTestCrash2():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_ubsan_div_by_zero.txt").read_text().splitlines(),
    )
    assert crashInfo.createShortSignature() == (
        "UndefinedBehaviorSanitizer: src/opus_demo.c:870:40: "
        "runtime error: division by zero"
    )
    assert len(crashInfo.backtrace) == 3
    assert crashInfo.backtrace[0] == "main"
    assert crashInfo.crashAddress is None


def test_UBSanParserTestCrash3():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_ubsan_missing_pattern.txt").read_text().splitlines(),
    )
    assert crashInfo.createShortSignature() == "No crash detected"
    assert len(crashInfo.backtrace) == 0
    assert crashInfo.crashAddress is None


def test_UBSanParserTestCrash4():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_ubsan_generic_crash.txt").read_text().splitlines(),
    )
    assert crashInfo.createShortSignature() == ("[@ mozilla::dom::ToJSValue]")
    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "mozilla::dom::ToJSValue"
    assert crashInfo.backtrace[1] == "js::jit::DoCallFallback"

    assert crashInfo.crashAddress == 0x000000004141
    assert crashInfo.registers["pc"] == 0x7F070B805037
    assert crashInfo.registers["bp"] == 0x7F06626006B0
    assert crashInfo.registers["sp"] == 0x7F0662600680


def test_UBSanParserTestCrash5():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_ubsan_div_by_zero_no_trace.txt")
        .read_text()
        .splitlines(),
    )
    assert crashInfo.createShortSignature() == (
        "UndefinedBehaviorSanitizer: src/opus_demo.c:870:40: "
        "runtime error: division by zero"
    )
    assert not crashInfo.backtrace
    assert crashInfo.crashAddress is None


def test_UBSanParserTestCrash6():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_ubsan_generic_crash_no_trace.txt")
        .read_text()
        .splitlines(),
    )
    assert crashInfo.createShortSignature() == ("[@ ??]")
    assert not crashInfo.backtrace
    assert crashInfo.crashAddress == 0x000000004141
    assert crashInfo.registers["pc"] == 0x7F070B805037
    assert crashInfo.registers["bp"] == 0x7F06626006B0
    assert crashInfo.registers["sp"] == 0x7F0662600680


def test_RustParserTests1():
    """test RUST_BACKTRACE=1 is parsed correctly"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_rust_sample_1.txt").read_text().splitlines(),
    )
    assert isinstance(crashInfo, RustCrashInfo)
    assert crashInfo.createShortSignature() == (
        "thread 'StyleThread#2' panicked at "
        "'assertion failed: self.get_data().is_some()', "
        "/home/worker/workspace/build/src/servo/components/"
        "style/gecko/wrapper.rs:976"
    )
    assert len(crashInfo.backtrace) == 20
    assert (
        crashInfo.backtrace[0]
        == "std::sys::imp::backtrace::tracing::imp::unwind_backtrace"
    )
    assert crashInfo.backtrace[14] == (
        "<style::gecko::traversal::RecalcStyleOnly<'recalc> as "
        "style::traversal::DomTraversal<style::gecko::wrapper::"
        "GeckoElement<'le>>>::process_preorder"
    )
    assert crashInfo.backtrace[19] == "<unknown>"
    assert crashInfo.crashAddress == 0


def test_RustParserTests2():
    """test RUST_BACKTRACE=full is parsed correctly"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_rust_sample_2.txt").read_text().splitlines(),
    )
    assert isinstance(crashInfo, RustCrashInfo)
    assert crashInfo.createShortSignature() == (
        "thread 'StyleThread#3' panicked at "
        "'assertion failed: self.get_data().is_some()', "
        "/home/worker/workspace/build/src/servo/components/style/"
        "gecko/wrapper.rs:1040"
    )
    assert len(crashInfo.backtrace) == 21
    assert (
        crashInfo.backtrace[0]
        == "std::sys::imp::backtrace::tracing::imp::unwind_backtrace"
    )
    assert crashInfo.backtrace[14] == (
        "<style::gecko::traversal::RecalcStyleOnly<'recalc> as "
        "style::traversal::DomTraversal<style::gecko::wrapper::"
        "GeckoElement<'le>>>::process_preorder"
    )
    assert crashInfo.backtrace[20] == "<unknown>"
    assert crashInfo.crashAddress == 0
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_rust_sample_3.txt").read_text().splitlines(),
    )
    assert isinstance(crashInfo, RustCrashInfo)
    assert crashInfo.createShortSignature() == (
        "thread 'StyleThread#2' panicked at "
        "'already mutably borrowed', /home/worker/workspace/build/"
        "src/third_party/rust/atomic_refcell/src/lib.rs:161"
    )
    assert len(crashInfo.backtrace) == 7
    assert (
        crashInfo.backtrace[0]
        == "std::sys::imp::backtrace::tracing::imp::unwind_backtrace"
    )
    assert crashInfo.backtrace[3] == "std::panicking::rust_panic_with_hook"
    assert crashInfo.backtrace[6] == (
        "<style::values::specified::color::Color as style::values::computed"
        "::ToComputedValue>::to_computed_value"
    )
    assert crashInfo.crashAddress == 0


def test_RustParserTests3():
    """test rust backtraces are weakly found, ie. minidump output wins even if it comes
    after"""
    config = ProgramConfiguration("test", "x86-64", "win")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_rust_sample_4.txt").read_text().splitlines(),
    )
    assert isinstance(crashInfo, MinidumpCrashInfo)
    assert crashInfo.createShortSignature() == (
        r"thread 'StyleThread#2' panicked at "
        r"'already mutably borrowed', "
        r"Z:\build\build\src\third_party\rust\atomic_"
        r"refcell\src\lib.rs:161"
    )
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "std::panicking::rust_panic_with_hook"
    assert crashInfo.backtrace[1] == "std::panicking::begin_panic<&str>"
    assert crashInfo.backtrace[2] == "atomic_refcell::AtomicBorrowRef::do_panic"
    assert (
        crashInfo.backtrace[3]
        == "style::values::specified::color::{{impl}}::to_computed_value"
    )
    assert crashInfo.crashAddress == 0x7FFC41F2F276


def test_RustParserTests4():
    """test another rust backtrace"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_rust_sample_5.txt").read_text().splitlines(),
    )
    assert isinstance(crashInfo, RustCrashInfo)
    assert crashInfo.createShortSignature() == (
        "thread 'RenderBackend' panicked at 'called "
        "`Option::unwrap()` on a `None` value', /checkout/src/"
        "libcore/option.rs:335:20"
    )
    assert len(crashInfo.backtrace) == 3
    assert (
        crashInfo.backtrace[0]
        == "std::sys::imp::backtrace::tracing::imp::unwind_backtrace"
    )
    assert crashInfo.backtrace[1] == "std::panicking::default_hook::{{closure}}"
    assert crashInfo.backtrace[2] == "std::panicking::default_hook"
    assert crashInfo.crashAddress == 0


def test_RustParserTests5():
    """test multi-line with minidump trace in sterror rust backtrace"""
    auxData = [
        "OS|Linux|0.0.0 Linux ... x86_64",
        "CPU|amd64|family 6 model 63 stepping 2|8",
        "GPU|||",
        "Crash|SIGSEGV|0x0|0",
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
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        (FIXTURE_PATH / "trace_rust_sample_6.txt").read_text().splitlines(),
        config,
        auxData,
    )
    assert isinstance(crashInfo, MinidumpCrashInfo)
    assert (
        "panicked at 'assertion failed: `(left == right)`"
        in crashInfo.createShortSignature()
    )
    assert len(crashInfo.backtrace) == 3
    assert crashInfo.backtrace[0] == "mozalloc_abort"
    assert crashInfo.backtrace[1] == "abort"
    assert crashInfo.backtrace[2] == "panic_abort::__rust_start_panic"
    assert crashInfo.crashAddress == 0


def test_RustParserTests6():
    """test parsing rust assertion failure backtrace"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        (FIXTURE_PATH / "trace_rust_sample_6.txt").read_text().splitlines(),
        config,
        [],
    )
    assert isinstance(crashInfo, RustCrashInfo)
    assert (
        "panicked at 'assertion failed: `(left == right)`"
        in crashInfo.createShortSignature()
    )
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[1] == "std::sys_common::backtrace::_print"
    assert crashInfo.crashAddress == 0


def test_MinidumpModuleInStackTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_minidump_swrast.txt").read_text().splitlines(),
    )
    assert crashInfo.backtrace[0] == "??"
    assert crashInfo.backtrace[1] == "swrast_dri.so+0x470ecc"


def test_LSanParserTestLeakDetected():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_lsan_leak_detected.txt").read_text().splitlines(),
    )
    assert crashInfo.createShortSignature() == ("LeakSanitizer: [@ malloc]")
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "malloc"
    assert crashInfo.backtrace[1] == "moz_xmalloc"
    assert crashInfo.backtrace[2] == "operator new"
    assert crashInfo.backtrace[3] == "mozilla::net::nsStandardURL::StartClone"
    assert crashInfo.crashAddress is None


def test_TSanParserSimpleLeakTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "tsan-simple-leak-report.txt").read_text().splitlines(),
    )

    assert crashInfo.createShortSignature() == (
        "ThreadSanitizer: thread leak [@ pthread_create]"
    )

    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "pthread_create"
    assert crashInfo.backtrace[1] == "main"

    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_TSanParserSimpleRaceTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    for fn in ["tsan-simple-race-report.txt", "tsan-simple-race-report-swapped.txt"]:
        crashInfo = CrashInfo.fromRawCrashData(
            [], [], config, (FIXTURE_PATH / fn).read_text().splitlines()
        )

        assert crashInfo.createShortSignature() == (
            "ThreadSanitizer: data race [@ foo1] vs. [@ foo2]"
        )

        assert len(crashInfo.backtrace) == 8
        assert crashInfo.backtrace[0] == "foo1"
        assert crashInfo.backtrace[1] == "bar1"
        assert crashInfo.backtrace[2] == "Thread1"
        assert crashInfo.backtrace[3] == "foo2"
        assert crashInfo.backtrace[4] == "bar2"

        assert crashInfo.crashInstruction is None
        assert crashInfo.crashAddress is None


def test_TSanParserLockReportTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "tsan-lock-report.txt").read_text().splitlines()
    )

    assert crashInfo.createShortSignature() == (
        "ThreadSanitizer: lock-order-inversion (potential deadlock) [@ PR_Lock]"
    )

    assert len(crashInfo.backtrace) == 12
    assert crashInfo.backtrace[0] == "pthread_mutex_lock"
    assert crashInfo.backtrace[1] == "PR_Lock"
    assert crashInfo.backtrace[2] == "sftk_hasAttribute"
    assert crashInfo.backtrace[3] == "sftk_CopyObject"
    assert crashInfo.backtrace[4] == "pthread_mutex_lock"

    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_TSanParserTestCrash():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "trace_tsan_crash.txt").read_text().splitlines()
    )
    assert crashInfo.createShortSignature() == "[@ mozalloc_abort]"
    assert len(crashInfo.backtrace) == 6
    assert crashInfo.backtrace[0] == "mozalloc_abort"
    assert crashInfo.backtrace[1] == "mozalloc_handle_oom"
    assert crashInfo.backtrace[2] == "GeckoHandleOOM"
    assert crashInfo.backtrace[3] == "gkrust_shared::oom_hook::hook"
    assert crashInfo.backtrace[4] == "swrast_dri.so+0x75dc33"
    assert crashInfo.backtrace[5] == "<missing>"

    assert crashInfo.crashAddress == 0
    assert crashInfo.registers["pc"] == 0x559ED71AA5E3
    assert crashInfo.registers["bp"] == 0x033
    assert crashInfo.registers["sp"] == 0x7FE1A51BCF00


def test_TSanParserTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "tsan-report.txt").read_text().splitlines()
    )

    assert crashInfo.createShortSignature() == (
        "ThreadSanitizer: data race "
        "[@ js::ProtectedData<js::CheckMainThread"
        "<(js::AllowedHelperThread)0>, unsigned long>::operator++] "
        "vs. [@ js::gc::GCRuntime::majorGCCount]"
    )

    assert len(crashInfo.backtrace) == 146
    assert crashInfo.backtrace[1] == "js::gc::GCRuntime::incMajorGcNumber"
    assert crashInfo.backtrace[5] == "js::gc::GCRuntime::gcIfNeededAtAllocation"

    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_TSanParserTestClang14():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_tsan_clang14.txt").read_text().splitlines(),
    )
    assert (
        "ThreadSanitizer: data race [@ operator new] vs. [@ pthread_mutex_lock]"
        == crashInfo.createShortSignature()
    )
    assert crashInfo.crashAddress is None
    assert crashInfo.crashInstruction is None
    assert len(crashInfo.backtrace) == 166
    assert crashInfo.backtrace[0] == "operator new"
    assert crashInfo.backtrace[5:9] == [
        "pthread_mutex_lock",
        "libLLVM-12.so.1+0xb6f3ea",
        "nsThread::ThreadFunc",
        "_pt_root",
    ]


def test_ValgrindCJMParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-cjm-01.txt").read_text().splitlines()
    )

    assert crashInfo.createShortSignature() == (
        "Valgrind: Conditional jump or move depends on uninitialised value(s) "
        "[@ PyObject_Free]"
    )
    assert len(crashInfo.backtrace) == 7
    assert crashInfo.backtrace[0] == "PyObject_Free"
    assert crashInfo.backtrace[1] == "/usr/bin/python3.6"
    assert crashInfo.backtrace[3] == "main"
    assert crashInfo.backtrace[-1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None

    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-cjm-02.txt").read_text().splitlines()
    )

    assert crashInfo.createShortSignature() == (
        "Valgrind: Conditional jump or move depends on uninitialised value(s) "
        "[@ strlen]"
    )
    assert len(crashInfo.backtrace) == 5
    assert crashInfo.backtrace[0] == "strlen"
    assert crashInfo.backtrace[1] == "puts"
    assert crashInfo.backtrace[3] == "(below main)"
    assert crashInfo.backtrace[4] == "/home/user/a.out"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_ValgrindIRWParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-ir-01.txt").read_text().splitlines()
    )

    assert (
        crashInfo.createShortSignature()
        == "Valgrind: Invalid read of size 4 [@ blah_func]"
    )
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "blah_func"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.backtrace[-1] == "asdf"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0xBADF00D

    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-ir-02.txt").read_text().splitlines()
    )

    assert (
        crashInfo.createShortSignature() == "Valgrind: Invalid read of size 4 [@ main]"
    )
    assert len(crashInfo.backtrace) == 1
    assert crashInfo.backtrace[0] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0x5204068

    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-iw-01.txt").read_text().splitlines()
    )

    assert (
        crashInfo.createShortSignature()
        == "Valgrind: Invalid write of size 8 [@ memcpy]"
    )
    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "memcpy"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0x41414141


def test_ValgrindUUVParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-uuv-01.txt").read_text().splitlines()
    )

    assert (
        crashInfo.createShortSignature()
        == "Valgrind: Use of uninitialised value of size 8 [@ foo<123>::Init]"
    )
    assert len(crashInfo.backtrace) == 5
    assert crashInfo.backtrace[0] == "foo<123>::Init"
    assert crashInfo.backtrace[
        1
    ], "bar::func<bar::Init()::$_0, Promise<type1, type2 == true> >::Run"
    assert crashInfo.backtrace[2] == "non-virtual thunk to Run"
    assert crashInfo.backtrace[-1] == "posix_memalign"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_ValgrindIFParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-if-01.txt").read_text().splitlines()
    )

    assert (
        crashInfo.createShortSignature()
        == "Valgrind: Invalid free() / delete / delete[] / realloc() [@ free]"
    )
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "free"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.backtrace[-1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0x43F2931

    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-if-02.txt").read_text().splitlines()
    )

    assert (
        crashInfo.createShortSignature()
        == "Valgrind: Invalid free() / delete / delete[] / realloc() [@ free]"
    )
    assert len(crashInfo.backtrace) == 6
    assert crashInfo.backtrace[0] == "free"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.backtrace[-1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0x5204040

    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-if-03.txt").read_text().splitlines()
    )

    assert (
        crashInfo.createShortSignature()
        == "Valgrind: Invalid free() / delete / delete[] / realloc() [@ free]"
    )
    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "free"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0xBADF00D


def test_ValgrindSDOParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-sdo-01.txt").read_text().splitlines()
    )

    assert crashInfo.createShortSignature() == (
        "Valgrind: Source and destination overlap [@ memcpy]"
    )
    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "memcpy"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_ValgrindSCParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-sc-01.txt").read_text().splitlines()
    )

    assert crashInfo.createShortSignature() == (
        "Valgrind: Syscall param write(buf) points to uninitialised byte(s) [@ write]"
    )
    assert len(crashInfo.backtrace) == 6
    assert crashInfo.backtrace[0] == "write"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.backtrace[-1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0x522E040

    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-sc-02.txt").read_text().splitlines()
    )

    assert crashInfo.createShortSignature() == (
        "Valgrind: Syscall param socketcall.sendto(msg) points to uninitialised byte(s)"
        " [@ send]"
    )
    assert len(crashInfo.backtrace) == 5
    assert crashInfo.backtrace[0] == "send"
    assert crashInfo.backtrace[2] == "start_thread"
    assert crashInfo.backtrace[-1] == "start_thread"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0x5E7B6B4


def test_ValgrindNMParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-nm-01.txt").read_text().splitlines()
    )

    assert crashInfo.createShortSignature() == (
        "Valgrind: Argument 'size' of function malloc has a fishy (possibly negative) "
        "value: -1 [@ malloc]"
    )
    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "malloc"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_ValgrindPTParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-pt-01.txt").read_text().splitlines()
    )

    assert crashInfo.createShortSignature() == (
        "Valgrind: Process terminating with default action of signal 11 (SIGSEGV) "
        "[@ strlen]"
    )
    assert len(crashInfo.backtrace) == 3
    assert crashInfo.backtrace[0] == "strlen"
    assert crashInfo.backtrace[2] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_ValgrindLeakParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-leak-01.txt").read_text().splitlines()
    )

    assert crashInfo.createShortSignature() == (
        "Valgrind: 102,400 bytes in 1,024 blocks are definitely lost [@ malloc]"
    )
    assert len(crashInfo.backtrace) == 3
    assert crashInfo.backtrace[0] == "malloc"
    assert crashInfo.backtrace[2] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None

    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [], [], config, (FIXTURE_PATH / "valgrind-leak-02.txt").read_text().splitlines()
    )

    assert crashInfo.createShortSignature() == (
        "Valgrind: 16 bytes in 1 blocks are possibly lost [@ malloc]"
    )
    assert len(crashInfo.backtrace) == 3
    assert crashInfo.backtrace[0] == "malloc"
    assert crashInfo.backtrace[2] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_SanitizerSoftRssLimitHeapProfile():
    """test that heap profile given after soft rss limit is exceeded
    is used in place of the (useless) SEGV stack"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_asan_soft_rss_heap_report.txt").read_text().splitlines(),
    )

    assert crashInfo.createShortSignature() == "[@ __interceptor_calloc]"
    assert len(crashInfo.backtrace) == 153
    assert crashInfo.backtrace[0] == "__interceptor_calloc"
    assert (
        crashInfo.backtrace[8] == "webrender_bindings::moz2d_renderer::rasterize_blob"
    )
    assert crashInfo.backtrace[-1] == "wl_display_dispatch_queue_pending"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 40


def test_SanitizerHardRssLimitHeapProfile():
    """test that heap profile given after hard rss limit is exceeded
    is used in place of the (useless) SEGV stack"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData(
        [],
        [],
        config,
        (FIXTURE_PATH / "trace_asan_hard_rss_heap_report.txt").read_text().splitlines(),
    )

    assert crashInfo.createShortSignature() == (
        "AddressSanitizer: hard rss limit exhausted"
    )
    assert len(crashInfo.backtrace) == 32
    assert crashInfo.backtrace[0] == "__interceptor_realloc"
    assert crashInfo.backtrace[9] == "webrender::image_tiling::for_each_tile_in_range"
    assert crashInfo.backtrace[-1] == "start_thread"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_unicode_escape():
    """test that unicode special and control characters are escaped"""

    @unicode_escape_result
    def testfunc():
        return """ü\ufffdシ\u008dAن"""

    assert testfunc() == r"""ü\u{fffd}シ\u{8d}Aن"""
