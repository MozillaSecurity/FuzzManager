# coding: utf-8
'''
Created on Oct 9, 2014

@author: decoder
'''
import json
import os

from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures.CrashInfo import CrashInfo
from FTB.Signatures.CrashSignature import CrashSignature
from FTB.Signatures.Matchers import StringMatch
from FTB.Signatures.Symptom import OutputSymptom, StackFramesSymptom

CWD = os.path.dirname(os.path.realpath(__file__))


testTrace1 = """Program received signal SIGSEGV, Segmentation fault.
GetObjectAllocKindForCopy (obj=0x7ffff54001b0, nursery=...) at /srv/repos/mozilla-central/js/src/gc/Nursery.cpp:369
369         if (obj->is<ArrayObject>()) {
#0  GetObjectAllocKindForCopy (obj=0x7ffff54001b0, nursery=...) at /srv/repos/mozilla-central/js/src/gc/Nursery.cpp:369
#1  js::Nursery::moveToTenured (this=0x1673be0, trc=0x7fffffffa2d0, src=<optimized out>) at /srv/repos/mozilla-central/js/src/gc/Nursery.cpp:570
#2  0x00000000004d167a in MinorGCCallback (thingp=0x7fffffff9fd0, jstrc=<optimized out>, kind=<optimized out>) at /srv/repos/mozilla-central/js/src/gc/Nursery.cpp:721
#3  js::Nursery::MinorGCCallback (jstrc=<optimized out>, thingp=0x7fffffff9fd0, kind=<optimized out>) at /srv/repos/mozilla-central/js/src/gc/Nursery.cpp:717
#4  0x00000000004b8690 in MarkInternal<JSObject> (trc=0x7fffffffa2d0, thingp=<optimized out>) at /srv/repos/mozilla-central/js/src/gc/Marking.cpp:317
#5  0x00000000004cc55e in MarkValueInternal (v=0x7fffffffa5d8, trc=0x7fffffffa2d0) at /srv/repos/mozilla-central/js/src/gc/Marking.cpp:804
#6  MarkValueInternal (v=0x7fffffffa5d8, trc=0x7fffffffa2d0) at /srv/repos/mozilla-central/js/src/gc/Marking.cpp:827
#7  js::gc::MarkValueRoot (trc=<optimized out>, v=0x7fffffffa5d8, name=<optimized out>) at /srv/repos/mozilla-central/js/src/gc/Marking.cpp:831
rax     0x2b2b2b2b      3110627432037296939
rbx     0xf54001b0      140737308000688
rcx     0xbad0bad1      3134241489
rdx     0x1656120       23421216
rsi     0xffffa2d0      140737488331472
rdi     0x1673be0       23542752
rbp     0xf54001b0      140737308000688
rsp     0xffff9f10      140737488330512
r8      0x0     0
r9      0x0     0
r10     0x1     1
r11     0x1     1
r12     0x0     -1266637395197952
r13     0xffffa2d0      140737488331472
r14     0x1673be0       23542752
r15     0x201   513
rip     0x4d0b32 <js::Nursery::moveToTenured(js::gc::MinorCollectionTracer*, JSObject*)+34>
=> 0x4d0b32 <js::Nursery::moveToTenured(js::gc::MinorCollectionTracer*, JSObject*)+34>: mov    (%rax),%r8
"""  # noqa

testTrace2 = """Program terminated with signal 11, Segmentation fault.
#0  JSObject::markChildren (this=0x7fc33ef5a060, trc=0x3538be0)
    at /srv/repos/mozilla-central/js/src/jsobj.cpp:4081
4081        if (clasp->trace)
Loading JavaScript value pretty-printers; see js/src/gdb/README.
If they cause trouble, type: disable pretty-printer .* SpiderMonkey
#0  JSObject::markChildren (this=(JSObject * const) 0x7fc33ef5a060 Cannot access memory at address 0x4949494949494949, trc=0x3538be0) at /srv/repos/mozilla-central/js/src/jsobj.cpp:4081
#1  0x00000000004e11e3 in MarkChildren (obj=(JSObject *) 0x7fc33ef5a060 Cannot access memory at address 0x4949494949494949, trc=0x3538be0) at /srv/repos/mozilla-central/js/src/gc/Marking.cpp:1323
#2  js::TraceChildren (trc=0x3538be0, thing=0x7fc33ef5a060, kind=<optimized out>) at /srv/repos/mozilla-central/js/src/gc/Marking.cpp:1934
#3  0x0000000000625d87 in js::gc::GCRuntime::startVerifyPreBarriers (this=this@entry=0x33ac568) at /srv/repos/mozilla-central/js/src/gc/Verifier.cpp:239
#4  0x0000000000633a5e in maybeVerifyPreBarriers (always=<optimized out>, this=0x33ac568) at /srv/repos/mozilla-central/js/src/gc/Verifier.cpp:563
#5  js::gc::MaybeVerifyBarriers (cx=<optimized out>, always=<optimized out>) at /srv/repos/mozilla-central/js/src/gc/Verifier.cpp:588
#6  0x00000000007c8660 in js::jit::CheckOverRecursedWithExtra (cx=0x33ce390, frame=<optimized out>, extra=<optimized out>, earlyCheck=<optimized out>) at /srv/repos/mozilla-central/js/src/jit/VMFunctions.cpp:153
#7  0x00007fc33ee95394 in ?? ()
#8  0x0000000000000000 in ?? ()
rax    0x4949494949494949    5280832617179597129
rbx    0x7fc33ef5a060    140476551635040
rcx    0x4949494949494949    5280832617179597129
rdx    0x4    4
rsi    0xa8ae16    11054614
rdi    0x3538be0    55806944
rbp    0x3538be0    55806944
rsp    0x7fff9aec80c0    140735792578752
r8    0x0    0
r9    0x2cd1    11473
r10    0x37d2580    58533248
r11    0x4000    16384
r12    0x7fc3240c5030    140476100137008
r13    0x2    2
r14    0x7fc3240c4ff0    140476100136944
r15    0x0    0
rip    0x84de35 <JSObject::markChildren(JSTracer*)+53>
=> 0x84de35 <JSObject::markChildren(JSTracer*)+53>:    mov    (%rax),%rax
   0x84de38 <JSObject::markChildren(JSTracer*)+56>:    mov    0x68(%rax),%rax
"""  # noqa

testTrace3 = """ASAN:SIGSEGV
=================================================================
==7116==ERROR: AddressSanitizer: SEGV on unknown address 0x000000000010 (pc 0x0000014662ba sp 0x7fffe804f180 bp 0x7fffe804f250 T0)
    #0 0x14662b9 in JSObject::getClass() const /home/ownhero/homes/mozilla/repos/mozilla-central/js/src/jsobj.h:128
    #1 0x14662b9 in bool JSObject::is<js::PropertyIteratorObject>() const /home/ownhero/homes/mozilla/repos/mozilla-central/js/src/jsobj.h:520
    #2 0x14662b9 in js::CloseIterator(JSContext*, JS::Handle<JSObject*>) /home/ownhero/homes/mozilla/repos/mozilla-central/js/src/jsiter.cpp:1065
    #3 0x14668e2 in js::UnwindIteratorForException(JSContext*, JS::Handle<JSObject*>) /home/ownhero/homes/mozilla/repos/mozilla-central/js/src/jsiter.cpp:1100
    #4 0xe989c0 in js::jit::CloseLiveIterator(JSContext*, js::jit::InlineFrameIterator const&, unsigned int) /home/ownhero/homes/mozilla/repos/mozilla-central/js/src/jit/JitFrames.cpp:388
    #5 0xe989c0 in js::jit::HandleExceptionIon(JSContext*, js::jit::InlineFrameIterator const&, js::jit::ResumeFromException*, bool*) /home/ownhero/homes/mozilla/repos/mozilla-central/js/src/jit/JitFrames.cpp:464
    #6 0xe989c0 in js::jit::HandleException(js::jit::ResumeFromException*) /home/ownhero/homes/mozilla/repos/mozilla-central/js/src/jit/JitFrames.cpp:782

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV /home/ownhero/homes/mozilla/repos/mozilla-central/js/src/jsobj.h:128 JSObject::getClass() const
==7116==ABORTING
"""  # noqa

testTraceHeapWithCrashAddress = """
Program terminated with signal 11, Segmentation fault.
#0  0xe1afa070 in ?? ()
#0  0xe1afa070 in ?? ()
#1  0x00000000 in ?? ()
eax    0xfff869cc    -497204
ebx    0x9469ff4    155623412
ecx    0xe20f6cc0    -502305600
edx    0xe1afa070    -508583824
esi    0xfff86934    -497356
edi    0xfff868cc    -497460
ebp    0xe20f8790    3792668560
esp    0xfff8682c    4294469676
eip    0xe1afa070    3786383472
=> 0xe1afa070:    push   %edi
   0xe1afa071:    push   %esi
"""

testTraceHeapWithoutCrashAddress = """
Program terminated with signal SIGSEGV, Segmentation fault.
#0  0x00007f2b41e78087 in ?? ()
#1  0xfff9000000000000 in ?? ()
#2  0x4275203ba1949000 in ?? ()
#3  0x00007fff5330bb01 in ?? ()
#4  0x00007f2b44d83e40 in ?? ()
rax    0x7f2b42c45bc0    139823780486080
rbx    0x0    0
rcx    0x4275203ba1949000    4788769219264417792
rdx    0x1    1
rsi    0x7f2b42c4a310    139823780504336
rdi    0x7f2b4aa19000    139823912423424
rbp    0x7f2b42c4a310    139823780504336
rsp    0x7fff5330bae0    140734589090528
r8    0x7f2b46261678    139823837222520
r9    0x0    0
r10    0x7f2b46261688    139823837222536
r11    0x7f2b4aa6a1e8    139823912755688
r12    0x0    0
r13    0x7b2    1970
r14    0x404    1028
r15    0x7f2b4aa19000    139823912423424
rip    0x7f2b41e78087    139823766012039
=> 0x7f2b41e78087:    xorpd  %xmm5,%xmm5
   0x7f2b41e7808b:    ucomisd %xmm5,%xmm4
"""

testTraceWithAuxMessage = """
==19462==ERROR: AddressSanitizer: heap-use-after-free on address 0x7fd766c42800 at pc 0xe1f587 bp 0x7fffcb1b6ed0 sp 0x7fffcb1b6ec8
READ of size 6143520 at 0x7fd766c42800 thread T0
    #0 0xe1f586 in void mozilla::PodCopy<char16_t>(char16_t*, char16_t const*, unsigned long) /srv/repos/mozilla-central/js/src/opt64asan/js/src/../../dist/include/mozilla/PodOperations.h:110
    #1 0x5904e2 in js::frontend::CompileScript(js::ExclusiveContext*, js::LifoAlloc*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::ReadOnlyCompileOptions const&, char16_t const*, unsigned long, JSString*, unsigned int, js::SourceCompressionTask*) /srv/repos/mozilla-central/js/src/frontend/BytecodeCompiler.cpp:215
    #2 0xc7eb8d in JS::Compile(JSContext*, JS::Handle<JSObject*>, JS::ReadOnlyCompileOptions const&, char16_t const*, unsigned long) /srv/repos/mozilla-central/js/src/jsapi.cpp:4478
    #3 0x4f63a6 in Run(JSContext*, unsigned int, JS::Value*) /srv/repos/mozilla-central/js/src/shell/js.cpp:1193
"""  # noqa

testTraceWithAuxAndAbortMessage = """
Hit MOZ_CRASH(named lambda static scopes should have been skipped) at /srv/repos/mozilla-central/js/src/vm/ScopeObject.cpp:1277
==19462==ERROR: AddressSanitizer: heap-use-after-free on address 0x7fd766c42800 at pc 0xe1f587 bp 0x7fffcb1b6ed0 sp 0x7fffcb1b6ec8
READ of size 6143520 at 0x7fd766c42800 thread T0
    #0 0xe1f586 in void mozilla::PodCopy<char16_t>(char16_t*, char16_t const*, unsigned long) /srv/repos/mozilla-central/js/src/opt64asan/js/src/../../dist/include/mozilla/PodOperations.h:110
    #1 0x5904e2 in js::frontend::CompileScript(js::ExclusiveContext*, js::LifoAlloc*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::ReadOnlyCompileOptions const&, char16_t const*, unsigned long, JSString*, unsigned int, js::SourceCompressionTask*) /srv/repos/mozilla-central/js/src/frontend/BytecodeCompiler.cpp:215
    #2 0xc7eb8d in JS::Compile(JSContext*, JS::Handle<JSObject*>, JS::ReadOnlyCompileOptions const&, char16_t const*, unsigned long) /srv/repos/mozilla-central/js/src/jsapi.cpp:4478
    #3 0x4f63a6 in Run(JSContext*, unsigned int, JS::Value*) /srv/repos/mozilla-central/js/src/shell/js.cpp:1193
"""  # noqa

testTraceNegativeSizeParam = """
==12549==ERROR: AddressSanitizer: negative-size-param: (size=-17179869184)
    #0 0x4a4afb in __asan_memmove /src/llvm/projects/compiler-rt/lib/asan/asan_interceptors.cc:445:3
    #1 0x7f7d02324aa2 in MoveOverlappingRegion src/obj-firefox/dist/include/nsTArray.h:621:5
    #2 0x7f7d02324aa2 in ShiftData<nsTArrayInfallibleAllocator> /src/obj-firefox/dist/include/nsTArray-inl.h:272
    #3 0x7f7d02324aa2 in RemoveElementsAt /src/obj-firefox/dist/include/nsTArray.h:2061
    #4 0x7f7d02324aa2 in mozilla::a11y::HyperTextAccessible::InsertChildAt(unsigned int, mozilla::a11y::Accessible*) /src/accessible/generic/HyperTextAccessible.cpp:1914
    #5 0x7f7d02312322 in mozilla::a11y::DocAccessible::DoARIAOwnsRelocation(mozilla::a11y::Accessible*) /src/accessible/generic/DocAccessible.cpp:2089:19
"""  # noqa

testAsanStackOverflow = """
==9482==ERROR: AddressSanitizer: stack-overflow on address 0x7ffec10e9f58 (pc 0x0000004a5349 bp 0x7ffec10ea7b0 sp 0x7ffec10e9f60 T0)
    #0 0x4a5348 in __asan_memset /builds/slave/moz-toolchain/src/llvm/projects/compiler-rt/lib/asan/asan_interceptors.cc:430:3
    #1 0x7fc2baf40c75 in PropertyProvider::GetSpacingInternal(gfxTextRun::Range, gfxFont::Spacing*, bool) const /builds/worker/workspace/build/src/layout/generic/nsTextFrame.cpp:3445:29
    #2 0x7fc2b632ca48 in GetAdjustedSpacing /builds/worker/workspace/build/src/gfx/thebes/gfxTextRun.cpp:370:16
    #3 0x7fc2b632ca48 in gfxTextRun::GetAdjustedSpacingArray(gfxTextRun::Range, gfxTextRun::PropertyProvider*, gfxTextRun::Range, nsTArray<gfxFont::Spacing>*) const /builds/worker/workspace/build/src/gfx/thebes/gfxTextRun.cpp:403
    #4 0x7fc2b63317c7 in gfxTextRun::AccumulateMetricsForRun(gfxFont*, gfxTextRun::Range, gfxFont::BoundingBoxType, mozilla::gfx::DrawTarget*, gfxTextRun::PropertyProvider*, gfxTextRun::Range, mozilla::gfx::ShapedTextFlags, gfxFont::RunMetrics*) const /builds/worker/workspace/build/src/gfx/thebes/gfxTextRun.cpp:785:24
    #5 0x7fc2b6330885 in gfxTextRun::MeasureText(gfxTextRun::Range, gfxFont::BoundingBoxType, mozilla::gfx::DrawTarget*, gfxTextRun::PropertyProvider*) const /builds/worker/workspace/build/src/gfx/thebes/gfxTextRun.cpp:859:9
    #6 0x7fc2b6334328 in gfxTextRun::BreakAndMeasureText(unsigned int, unsigned int, bool, double, gfxTextRun::PropertyProvider*, gfxTextRun::SuppressBreak, double*, bool, gfxFont::RunMetrics*, gfxFont::BoundingBoxType, mozilla::gfx::DrawTarget*, bool*, unsigned int*, bool, gfxBreakPriority*) /builds/worker/workspace/build/src/gfx/thebes/gfxTextRun.cpp:1183:21
    #7 0x7fc2baf7cd24 in nsTextFrame::ReflowText(nsLineLayout&, int, mozilla::gfx::DrawTarget*, mozilla::ReflowOutput&, nsReflowStatus&) /builds/worker/workspace/build/src/layout/generic/nsTextFrame.cpp:9476:15
    #8 0x7fc2baeb732c in nsLineLayout::ReflowFrame(nsIFrame*, nsReflowStatus&, mozilla::ReflowOutput*, bool&) /builds/worker/workspace/build/src/layout/generic/nsLineLayout.cpp:924:7
"""  # noqa

testAsanAccessViolation = """
==5328==ERROR: AddressSanitizer: access-violation on unknown address 0x000000000050 (pc 0x7ffa9a30c9e7 bp 0x00f9915f0a20 sp 0x00f9915f0940 T0)
==5328==The signal is caused by a READ memory access.
==5328==Hint: address points to the zero page.
    #0 0x7ffa9a30c9e6 in nsCSSFrameConstructor::WipeContainingBlock z:\\build\\build\\src\\layout\\base\\nsCSSFrameConstructor.cpp:12715
    #1 0x7ffa9a3051d7 in nsCSSFrameConstructor::ContentAppended z:\\build\\build\\src\\layout\\base\\nsCSSFrameConstructor.cpp:7690
    #2 0x7ffa9a1f0241 in mozilla::RestyleManager::ProcessRestyledFrames z:\\build\\build\\src\\layout\\base\\RestyleManager.cpp:1414
"""  # noqa


testAsanLongTrace = """
==18896==ERROR: AddressSanitizer: stack-overflow on address 0x7ffcb3422c20 (pc 0x7f12fc7715a8 bp 0x7ffcb3423e90 sp 0x7ffcb3422c20 T0)
    #0 0x7f12fc7715a7 in nsLineBreaker::AppendText(nsAtom*, unsigned char const*, unsigned int, unsigned int, nsILineBreakSink*) /builds/worker/workspace/build/src/dom/base/nsLineBreaker.cpp
    #1 0x7f130185dfed in BuildTextRunsScanner::SetupBreakSinksForTextRun(gfxTextRun*, void const*) /builds/worker/workspace/build/src/layout/generic/nsTextFrame.cpp:2653:22
    #2 0x7f1301852baa in BuildTextRunsScanner::SetupLineBreakerContext(gfxTextRun*) /builds/worker/workspace/build/src/layout/generic/nsTextFrame.cpp:2545:3
    #3 0x7f1301850b62 in BuildTextRunsScanner::FlushFrames(bool, bool) /builds/worker/workspace/build/src/layout/generic/nsTextFrame.cpp:1679:12
    #4 0x7f1301861fd7 in BuildTextRuns /builds/worker/workspace/build/src/layout/generic/nsTextFrame.cpp:1624:11
    #5 0x7f1301861fd7 in nsTextFrame::EnsureTextRun(nsTextFrame::TextRunType, mozilla::gfx::DrawTarget*, nsIFrame*, nsLineList_iterator const*, unsigned int*) /builds/worker/workspace/build/src/layout/generic/nsTextFrame.cpp:2867
    #6 0x7f13018a5bb0 in nsTextFrame::ReflowText(nsLineLayout&, int, mozilla::gfx::DrawTarget*, mozilla::ReflowOutput&, nsReflowStatus&) /builds/worker/workspace/build/src/layout/generic/nsTextFrame.cpp:9412:5
    #7 0x7f13017d53bc in nsLineLayout::ReflowFrame(nsIFrame*, nsReflowStatus&, mozilla::ReflowOutput*, bool&) /builds/worker/workspace/build/src/layout/generic/nsLineLayout.cpp:927:7
    #8 0x7f1301610e7d in nsBlockFrame::ReflowInlineFrame(mozilla::BlockReflowInput&, nsLineLayout&, nsLineList_iterator, nsIFrame*, LineReflowStatus*) /builds/worker/workspace/build/src/layout/generic/nsBlockFrame.cpp:4158:15
    #9 0x7f130160f827 in nsBlockFrame::DoReflowInlineFrames(mozilla::BlockReflowInput&, nsLineLayout&, nsLineList_iterator, nsFlowAreaRect&, int&, nsFloatManager::SavedState*, bool*, LineReflowStatus*, bool) /builds/worker/workspace/build/src/layout/generic/nsBlockFrame.cpp:3958:5
    #10 0x7f1301606549 in nsBlockFrame::ReflowInlineFrames(mozilla::BlockReflowInput&, nsLineList_iterator, bool*) /builds/worker/workspace/build/src/layout/generic/nsBlockFrame.cpp:3832:9
    #11 0x7f13015feaa0 in nsBlockFrame::ReflowLine(mozilla::BlockReflowInput&, nsLineList_iterator, bool*) /builds/worker/workspace/build/src/layout/generic/nsBlockFrame.cpp:2816:5
    #12 0x7f13015f4320 in nsBlockFrame::ReflowDirtyLines(mozilla::BlockReflowInput&) /builds/worker/workspace/build/src/layout/generic/nsBlockFrame.cpp:2352:7
    #13 0x7f13015ebb34 in nsBlockFrame::Reflow(nsPresContext*, mozilla::ReflowOutput&, mozilla::ReflowInput const&, nsReflowStatus&) /builds/worker/workspace/build/src/layout/generic/nsBlockFrame.cpp:1225:3
    #14 0x7f130160cda7 in nsBlockReflowContext::ReflowBlock(mozilla::LogicalRect const&, bool, nsCollapsingMargin&, int, bool, nsLineBox*, mozilla::ReflowInput&, nsReflowStatus&, mozilla::BlockReflowInput&) /builds/worker/workspace/build/src/layout/generic/nsBlockReflowContext.cpp:306:11
    #15 0x7f1301600e23 in nsBlockFrame::ReflowBlockFrame(mozilla::BlockReflowInput&, nsLineList_iterator, bool*) /builds/worker/workspace/build/src/layout/generic/nsBlockFrame.cpp:3463:11
    #16 0x7f13015febf5 in nsBlockFrame::ReflowLine(mozilla::BlockReflowInput&, nsLineList_iterator, bool*) /builds/worker/workspace/build/src/layout/generic/nsBlockFrame.cpp:2813:5

SUMMARY: AddressSanitizer: stack-overflow dom/base/nsLineBreaker.cpp in nsLineBreaker::AppendText(nsAtom*, unsigned char const*, unsigned int, unsigned int, nsILineBreakSink*)
==18896==ABORTING
"""  # noqa

testAsanFailedAlloc = """
==18847==ERROR: AddressSanitizer failed to allocate 0x6003a000 (1610850304) bytes of LargeMmapAllocator (error code: 12)
==18847==Process memory map follows:
  0x08048000-0x081d7000 /foo/bar
  0xffb00000-0xffb21000 [stack]
==18847==End of process memory map.
==18847==AddressSanitizer CHECK failed: /build/llvm-toolchain-4.0-euGZ6h/llvm-toolchain-4.0-4.0/projects/compiler-rt/lib/sanitizer_common/sanitizer_common.cc:120 "((0 && "unable to mmap")) != (0)" (0x0, 0x0)
    #0 0x8127526 in __asan::AsanCheckFailed(char const*, int, char const*, unsigned long long, unsigned long long) (build/dump_video+0x8127526)
    #1 0x814262b in __sanitizer::CheckFailed(char const*, int, char const*, unsigned long long, unsigned long long) (build/dump_video+0x814262b)
    #2 0x8131f9a in __sanitizer::ReportMmapFailureAndDie(unsigned long, char const*, char const*, int, bool) (build/dump_video+0x8131f9a)
"""  # noqa

testSignature1 = '''{"symptoms": [
    {
    "functionName": "GetObjectAllocKindForCopy",
    "frameNumber": 0,
    "type": "stackFrame"
  },
    {
    "functionName": "js::Nursery::moveToTenured",
    "frameNumber": 1,
    "type": "stackFrame"
  },
    {
    "functionName": "MinorGCCallback",
    "frameNumber": 2,
    "type": "stackFrame"
  },
    {
    "functionName": "js::Nursery::MinorGCCallback",
    "frameNumber": 3,
    "type": "stackFrame"
  },
    {
    "address": "> 0xFF",
    "type": "crashAddress"
  }
]}
'''

testSignature2 = '''{"symptoms": [
    {
    "functionName": "GetObjectAllocKindForCopy",
    "frameNumber": 0,
    "type": "stackFrame"
  },
    {
    "functionName": "js::Nursery::moveToTenured",
    "frameNumber": 1,
    "type": "stackFrame"
  },
    {
    "functionName": "MinorGCCallback",
    "frameNumber": 2,
    "type": "stackFrame"
  }
]}
'''

testSignature3 = '''{"symptoms": [
    {
    "functionName": "GetObjectAllocKindForCopy",
    "frameNumber": 0,
    "type": "stackFrame"
  },
    {
    "functionName": "js::Nursery::moveToTenured",
    "frameNumber": 1,
    "type": "stackFrame"
  },
  {
    "address": "> 0xFF",
    "type": "crashAddress"
  },
    {
    "type": "instruction",
    "instructionName": "mov    (%rax),%r8"
  }
]}
'''

testSignature4 = '''{"symptoms": [
    {
    "functionName": "GetObjectAllocKindForCopy",
    "frameNumber": 0,
    "type": "stackFrame"
  },
    {
    "functionName": "js::Nursery::moveToTenured",
    "frameNumber": 1,
    "type": "stackFrame"
  },
    {
    "type": "testcase",
    "value": {
      "matchType": "pcre",
      "value": "SIMD\\\\.float\\\\d+x"
    }
  }
]}
'''

testSignature5 = '''{"symptoms": [
    {
    "functionName": "GetObjectAllocKindForCopy",
    "frameNumber": 0,
    "type": "stackFrame"
  },
    {
    "functionName": "js::Nursery::moveToTenured",
    "frameNumber": 1,
    "type": "stackFrame"
  },
    {
    "type": "testcase",
    "value": "SIMD.float32x4"
  }
]}
'''

testSignature6 = '''{"symptoms": [
    {
    "functionName": "GetObjectAllocKindForCopy",
    "frameNumber": 0,
    "type": "stackFrame"
  },
    {
    "functionName": "js::Nursery::moveToTenured",
    "frameNumber": 1,
    "type": "stackFrame"
  },
    {
    "type": "testcase",
    "value": "SIMD.float64x4"
  }
]}
'''

testSignature7 = '''{"symptoms": [
    {
      "type": "stackFrames",
      "functionNames": [
        "js::UnwindIteratorForException",
        "CloseLiveIterator",
        "HandleExceptionIon",
        "js::jit::HandleException"
      ]
    }
]}
'''

testCase1 = '''
function test() {
  var a = SIMD.float32x4();
  if (typeof reportCompare === "function")
    reportCompare(true, true);
}
test();
'''

testSignatureStackFrames1 = '''{"symptoms": [
    {
    "type": "stackFrames",
    "functionNames": [ "GetObjectAllocKindForCopy", "moveToTenured", "?", "MinorGCCallback", "MarkInternal<JSObject>" ]
  }
]}
'''

testSignatureStackFrames2 = '''{"symptoms": [
    {
    "type": "stackFrames",
    "functionNames": [ "GetObjectAllocKindForCopy", "moveToTenured", "?", "MinorGCCallback", "MinorGCCallback", "MarkInternal<JSObject>" ]
  }
]}
'''  # noqa

testSignatureStackFrames3 = '''{"symptoms": [
    {
    "type": "stackFrames",
    "functionNames": [ "GetObjectAllocKindForCopy", "moveToTenured", "?", "?", "MarkInternal<JSObject>" ]
  }
]}
'''

testSignatureStackFrames4 = '''{"symptoms": [
    {
    "type": "stackFrames",
    "functionNames": [ "GetObjectAllocKindForCopy", "moveToTenured", "???", "MarkInternal<JSObject>" ]
  }
]}
'''

testSignatureStackFrames5 = '''{"symptoms": [
    {
    "type": "stackFrames",
    "functionNames": [ "GetObjectAllocKindForCopy", "moveToTenured", "?", "MarkInternal<JSObject>" ]
  }
]}
'''


testSignaturePCREShort1 = '''{"symptoms": [
    {
    "functionName": "/.+KindForCopy/",
    "type": "stackFrame"
  }
]}
'''

testSignaturePCREShort2 = '''{"symptoms": [
    {
    "functionName": "/^.KindForCopy/",
    "type": "stackFrame"
  }
]}
'''

testSignatureEmptyCrashAddress = '''{"symptoms": [
  {
    "address": "",
    "type": "crashAddress"
  }
]}
'''

testSignatureStackSize = '''{"symptoms": [
  {
    "size": "> 15",
    "type": "stackSize"
  }
]}
'''

testAssertionPathFwSlashes = 'Assertion failure: false, at /srv/repos/mozilla-central/js/src/vm/SelfHosting.cpp:362'
testAssertionPathBwSlashes = r'Assertion failure: false, at c:\srv\repos\mozilla-central\js\src\vm\SelfHosting.cpp:362'


def test_SignatureCreateTest():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = CrashInfo.fromRawCrashData([], [], config, auxCrashData=testTrace1.splitlines())
    crashSig1 = crashInfo.createCrashSignature(forceCrashAddress=True, maxFrames=4, minimumSupportedVersion=10)
    crashSig2 = crashInfo.createCrashSignature(forceCrashAddress=False, maxFrames=3, minimumSupportedVersion=10)
    crashSig3 = crashInfo.createCrashSignature(forceCrashInstruction=True, maxFrames=2, minimumSupportedVersion=10)

    # Check that all generated signatures match their originating crashInfo
    assert crashSig1.matches(crashInfo)
    assert crashSig2.matches(crashInfo)
    assert crashSig3.matches(crashInfo)

    # Check that the generated signatures look as expected
    assert json.loads(str(crashSig1)) == json.loads(testSignature1)
    assert json.loads(str(crashSig2)) == json.loads(testSignature2)

    #  The third crashInfo misses 2 frames from the top 4 frames, so it will
    #  also include the crash address, even though we did not request it.
    assert json.loads(str(crashSig3)) == json.loads(testSignature3)


def test_SignatureTestCaseMatchTest():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = CrashInfo.fromRawCrashData([], [], config, auxCrashData=testTrace1.splitlines())

    testSig3 = CrashSignature(testSignature3)
    testSig4 = CrashSignature(testSignature4)
    testSig5 = CrashSignature(testSignature5)
    testSig6 = CrashSignature(testSignature6)

    assert not testSig3.matchRequiresTest()
    assert testSig4.matchRequiresTest()
    assert testSig5.matchRequiresTest()

    # Must not match without testcase provided
    assert not testSig4.matches(crashInfo)
    assert not testSig5.matches(crashInfo)
    assert not testSig6.matches(crashInfo)

    # Attach testcase
    crashInfo.testcase = testCase1

    # Must match with testcase provided
    assert testSig4.matches(crashInfo)
    assert testSig5.matches(crashInfo)

    # This one does not match at all
    assert not testSig6.matches(crashInfo)


def test_SignatureStackFramesTest():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = CrashInfo.fromRawCrashData([], [], config, auxCrashData=testTrace1.splitlines())

    testSig1 = CrashSignature(testSignatureStackFrames1)
    testSig2 = CrashSignature(testSignatureStackFrames2)
    testSig3 = CrashSignature(testSignatureStackFrames3)
    testSig4 = CrashSignature(testSignatureStackFrames4)
    testSig5 = CrashSignature(testSignatureStackFrames5)

    assert testSig1.matches(crashInfo)
    assert testSig2.matches(crashInfo)
    assert testSig3.matches(crashInfo)
    assert testSig4.matches(crashInfo)
    assert not testSig5.matches(crashInfo)


def test_SignatureStackFramesAlgorithmsTest():
    # Do some direct matcher tests on edge cases
    assert StackFramesSymptom._match([], [StringMatch('???')])
    assert not StackFramesSymptom._match([], [StringMatch('???'), StringMatch('a')])

    # Test the diff algorithm, test array contains:
    # stack, signature, expected distance, proposed signature
    testArray = [
        (['a', 'b', 'x', 'a', 'b', 'c'], ['a', 'b', '???', 'a', 'b', 'x', 'c'],
         1, ['a', 'b', '???', 'a', 'b', '?', 'c']),
        (['b', 'x', 'a', 'b', 'c'], ['a', 'b', '???', 'a', 'b', 'x', 'c'],
         2, ['?', 'b', '???', 'a', 'b', '?', 'c']),
        (['b', 'x', 'a', 'd', 'x'], ['a', 'b', '???', 'a', 'b', 'x', 'c'],
         3, ['?', 'b', '???', 'a', '?', 'x', '?']),
    ]

    for (stack, rawSig, expectedDepth, expectedSig) in testArray:
        for maxDepth in (expectedDepth, 3):
            (actualDepth, actualSig) = StackFramesSymptom._diff(stack,
                                                                [StringMatch(x) for x in rawSig], 0, 1, maxDepth)
            assert expectedDepth == actualDepth
            assert expectedSig == [str(x) for x in actualSig]


def test_SignaturePCREShortTest():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = CrashInfo.fromRawCrashData([], [], config, auxCrashData=testTrace1.splitlines())

    testSig1 = CrashSignature(testSignaturePCREShort1)
    testSig2 = CrashSignature(testSignaturePCREShort2)

    assert testSig1.matches(crashInfo)
    assert not testSig2.matches(crashInfo)


def test_SignatureStackFramesWildcardTailTest():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = CrashInfo.fromRawCrashData([], [], config, auxCrashData=testTrace2.splitlines())

    testSig = crashInfo.createCrashSignature()

    # Ensure that the last frame with a symbol is at the right place and there is nothing else,
    # espcially no wildcard, following afterwards.
    assert isinstance(testSig.symptoms[0], StackFramesSymptom)
    assert str(testSig.symptoms[0].functionNames[6]) == "js::jit::CheckOverRecursedWithExtra"
    assert len(testSig.symptoms[0].functionNames) == 7


def test_SignatureStackFramesRegressionTest():
    config = ProgramConfiguration("test", "x86", "linux")
    crashInfoNeg = CrashInfo.fromRawCrashData([], [], config,
                                              auxCrashData=testTraceHeapWithCrashAddress.splitlines())
    crashInfoPos = CrashInfo.fromRawCrashData([], [], config,
                                              auxCrashData=testTraceHeapWithoutCrashAddress.splitlines())

    testSigEmptyCrashAddress = CrashSignature(testSignatureEmptyCrashAddress)

    assert testSigEmptyCrashAddress.matches(crashInfoPos)
    assert not testSigEmptyCrashAddress.matches(crashInfoNeg)


def test_SignatureStackFramesAuxMessagesTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfoPos = CrashInfo.fromRawCrashData([], [], config, auxCrashData=testTraceWithAuxMessage.splitlines())
    crashInfoNeg = CrashInfo.fromRawCrashData([], [], config,
                                              auxCrashData=testTraceWithAuxAndAbortMessage.splitlines())

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
    crashInfoPos = CrashInfo.fromRawCrashData([], [], config, auxCrashData=testTraceNegativeSizeParam.splitlines())

    testSig = crashInfoPos.createCrashSignature()

    assert "/ERROR: AddressSanitizer" in str(testSig)
    assert "negative-size-param" in str(testSig)
    assert isinstance(testSig.symptoms[1], StackFramesSymptom)


def test_SignatureAsanStackOverflowTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfoPos = CrashInfo.fromRawCrashData([], [], config, auxCrashData=testAsanStackOverflow.splitlines())

    testSig = crashInfoPos.createCrashSignature()

    # Check matches appropriately
    assert testSig.matches(crashInfoPos)


def test_SignatureAsanAccessViolationTest():
    config = ProgramConfiguration("test", "x86-64", "windows")
    crashInfoPos = CrashInfo.fromRawCrashData([], [], config, auxCrashData=testAsanAccessViolation.splitlines())

    testSig = crashInfoPos.createCrashSignature()

    assert "/ERROR: AddressSanitizer" in str(testSig)
    assert "access-violation" in str(testSig)
    assert isinstance(testSig.symptoms[1], StackFramesSymptom)


def test_SignatureStackSizeTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfoPos = CrashInfo.fromRawCrashData([], [], config, auxCrashData=testAsanLongTrace.splitlines())

    # The test signature uses > 15 which was previously interpreted as 0x15
    # while the test crash data has 16 frames.
    testSig = CrashSignature(testSignatureStackSize)
    assert testSig.matches(crashInfoPos)


def test_SignatureAsanFailedAllocTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfoPos = CrashInfo.fromRawCrashData([], [], config, auxCrashData=testAsanFailedAlloc.splitlines())

    testSig = crashInfoPos.createCrashSignature()
    assert "/AddressSanitizer failed to allocate" in str(testSig)
    assert testSig.matches(crashInfoPos)
    assert isinstance(testSig.symptoms[1], StackFramesSymptom)


def test_SignatureGenerationTSanLeakTest():
    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, 'resources', 'tsan-simple-leak-report.txt'), 'r') as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, auxCrashData=f.read().splitlines())
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
    with open(os.path.join(CWD, 'resources', 'tsan-simple-race-report.txt'), 'r') as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, auxCrashData=f.read().splitlines())
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
        "(Previous )?[Ww]rite of size 4 at 0x[0-9a-fA-F]+ by thread T[0-9]+( .+mutexes: .+)?:",
        "(Previous )?[Rr]ead of size 4 at 0x[0-9a-fA-F]+ by main thread( .+mutexes: .+)?:"
    ]:
        found = False
        for symptom in outputSymptoms:
            if symptom.output.value == stringMatchVal:
                found = True
        assert found, "Couldn't find OutputSymptom with value '%s'" % stringMatchVal


def test_SignatureGenerationTSanRaceTestComplex1():
    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, 'resources', 'tsan-report2.txt'), 'r') as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, auxCrashData=f.read().splitlines())
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
        "(Previous )?[Ww]rite of size 8 at 0x[0-9a-fA-F]+ by thread T[0-9]+( .+mutexes: .+)?:",
        "(Previous )?[Ww]rite of size 8 at 0x[0-9a-fA-F]+ by thread T[0-9]+( .+mutexes: .+)?:"
    ]:
        found = False
        for symptom in outputSymptoms:
            if symptom.output.value == stringMatchVal:
                found = True
        assert found, "Couldn't find OutputSymptom with value '%s'" % stringMatchVal


def test_SignatureGenerationTSanRaceTestAtomic():
    config = ProgramConfiguration("test", "x86-64", "linux")
    for fn in ['tsan-report-atomic.txt', 'tsan-report-atomic-swapped.txt']:
        with open(os.path.join(CWD, 'resources', fn), 'r') as f:
            crashInfo = CrashInfo.fromRawCrashData([], [], config, auxCrashData=f.read().splitlines())

        assert(crashInfo.backtrace[0] == "pthread_mutex_destroy")
        assert(crashInfo.createShortSignature() ==
               "ThreadSanitizer: data race [@ pthread_mutex_destroy] vs. [@ pthread_mutex_unlock]")

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
            "(Previous )?[Aa]tomic [Rr]ead of size 1 at 0x[0-9a-fA-F]+ by thread T[0-9]+( .+mutexes: .+)?:",
            "(Previous )?[Ww]rite of size 1 at 0x[0-9a-fA-F]+ by main thread( .+mutexes: .+)?:"
        ]:
            found = False
            for symptom in outputSymptoms:
                if symptom.output.value == stringMatchVal:
                    found = True
            assert found, "Couldn't find OutputSymptom with value '%s'" % stringMatchVal


def test_SignatureMatchWithUnicode():
    config = ProgramConfiguration('test', 'x86-64', 'linux')
    crashInfo = CrashInfo.fromRawCrashData(["(Â«f => (generator.throw(f))Â», Â«undefinedÂ»)"], [], config)
    testSignature = CrashSignature('{"symptoms": [{"src": "stdout", "type": "output", "value": "x"}]}')
    assert not testSignature.matches(crashInfo)


def test_SignatureMatchAssertionSlashes():
    # test that a forward slash assertion signature matches a backwards slash crash, but only on windows
    cfg_linux = ProgramConfiguration('test', 'x86-64', 'linux')
    cfg_windows = ProgramConfiguration('test', 'x86-64', 'windows')

    fs_lines = testAssertionPathFwSlashes.splitlines()
    bs_lines = testAssertionPathBwSlashes.splitlines()

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
