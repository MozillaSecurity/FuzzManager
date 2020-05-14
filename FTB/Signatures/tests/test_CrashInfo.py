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
import os

from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures import RegisterHelper
from FTB.Signatures.CrashInfo import ASanCrashInfo, GDBCrashInfo, CrashInfo, \
    NoCrashInfo, MinidumpCrashInfo, AppleCrashInfo, CDBCrashInfo, RustCrashInfo, \
    int32
from FTB.Signatures.CrashSignature import CrashSignature

CWD = os.path.dirname(os.path.realpath(__file__))


asanTraceAV = """
==5328==ERROR: AddressSanitizer: access-violation on unknown address 0x000000000050 (pc 0x7ffa9a30c9e7 bp 0x00f9915f0a20 sp 0x00f9915f0940 T0)
==5328==The signal is caused by a READ memory access.
==5328==Hint: address points to the zero page.
    #0 0x7ffa9a30c9e6 in nsCSSFrameConstructor::WipeContainingBlock z:\\build\\build\\src\\layout\\base\\nsCSSFrameConstructor.cpp:12715
    #1 0x7ffa9a3051d7 in nsCSSFrameConstructor::ContentAppended z:\\build\\build\\src\\layout\\base\\nsCSSFrameConstructor.cpp:7690
    #2 0x7ffa9a1f0241 in mozilla::RestyleManager::ProcessRestyledFrames z:\\build\\build\\src\\layout\\base\\RestyleManager.cpp:1414
"""  # noqa

asanTraceCrash = """
ASAN:SIGSEGV
=================================================================
==5854==ERROR: AddressSanitizer: SEGV on unknown address 0x00000014 (pc 0x0810845f sp 0xffc57860 bp 0xffc57f18 T0)
    #0 0x810845e in js::AbstractFramePtr::asRematerializedFrame() const /srv/repos/mozilla-central/js/src/shell/../jit/RematerializedFrame.h:114
    #1 0x810845e in js::AbstractFramePtr::script() const /srv/repos/mozilla-central/js/src/shell/../vm/Stack-inl.h:572
    #2 0x810845e in EvalInFrame(JSContext*, unsigned int, JS::Value*) /srv/repos/mozilla-central/js/src/shell/js.cpp:2655
    #3 0x93f5b92 in js::CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), JS::CallArgs const&) /srv/repos/mozilla-central/js/src/jscntxtinlines.h:231
    #4 0x93f5b92 in js::Invoke(JSContext*, JS::CallArgs, js::MaybeConstruct) /srv/repos/mozilla-central/js/src/vm/Interpreter.cpp:484
    #5 0x9346ba7 in js::Invoke(JSContext*, JS::Value const&, JS::Value const&, unsigned int, JS::Value const*, JS::MutableHandle<JS::Value>) /srv/repos/mozilla-central/js/src/vm/Interpreter.cpp:540
    #6 0x8702baa in js::jit::DoCallFallback(JSContext*, js::jit::BaselineFrame*, js::jit::ICCall_Fallback*, unsigned int, JS::Value*, JS::MutableHandle<JS::Value>) /srv/repos/mozilla-central/js/src/jit/BaselineIC.cpp:8638

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV /srv/repos/mozilla-central/js/src/shell/../jit/RematerializedFrame.h:114 js::AbstractFramePtr::asRematerializedFrame() const
==5854==ABORTING
"""  # noqa

asanTraceHeapCrash = """
ASAN:SIGSEGV
=================================================================
==11923==ERROR: AddressSanitizer: SEGV on unknown address 0x00000019 (pc 0xf718072e sp 0xff87d130 bp 0x000006a1 T0)

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV ??:0 ??
==11923==ABORTING
"""

asanTraceUAF = """
==19462==ERROR: AddressSanitizer: heap-use-after-free on address 0x7fd766c42800 at pc 0xe1f587 bp 0x7fffcb1b6ed0 sp 0x7fffcb1b6ec8
READ of size 6143520 at 0x7fd766c42800 thread T0
    #0 0xe1f586 in void mozilla::PodCopy<char16_t>(char16_t*, char16_t const*, unsigned long) /srv/repos/mozilla-central/js/src/opt64asan/js/src/../../dist/include/mozilla/PodOperations.h:110
    #1 0x5904e2 in js::frontend::CompileScript(js::ExclusiveContext*, js::LifoAlloc*, JS::Handle<JSObject*>, JS::Handle<JSScript*>, JS::ReadOnlyCompileOptions const&, char16_t const*, unsigned long, JSString*, unsigned int, js::SourceCompressionTask*) /srv/repos/mozilla-central/js/src/frontend/BytecodeCompiler.cpp:215
    #2 0xc7eb8d in JS::Compile(JSContext*, JS::Handle<JSObject*>, JS::ReadOnlyCompileOptions const&, char16_t const*, unsigned long) /srv/repos/mozilla-central/js/src/jsapi.cpp:4478
    #3 0x4f63a6 in Run(JSContext*, unsigned int, JS::Value*) /srv/repos/mozilla-central/js/src/shell/js.cpp:1193
    #4 0xf8eb1b in JSFunction::native() const /srv/repos/mozilla-central/js/src/jscntxtinlines.h:220
    #5 0xf377c8 in js::Invoke(JSContext*, JS::Value const&, JS::Value const&, unsigned int, JS::Value*, JS::MutableHandle<JS::Value>) /srv/repos/mozilla-central/js/src/vm/Interpreter.cpp:521
    #6 0x82e98a in js::jit::DoCallFallback(JSContext*, js::jit::BaselineFrame*, js::jit::ICCall_Fallback*, unsigned int, JS::Value*, JS::MutableHandle<JS::Value>) /srv/repos/mozilla-central/js/src/jit/BaselineIC.cpp:8103
    #7 0x7fd76b2b1323 in
0x7fd766c42800 is located 0 bytes inside of 6143522-byte region [0x7fd766c42800,0x7fd76721e622)
freed by thread T0 here:
    #0 0x4c6855 in __interceptor_free _asan_rtl_
    #1 0xf0f898 in js_free(void*) /srv/repos/mozilla-central/js/src/opt64asan/js/src/../../dist/include/js/Utility.h:167
    #2 0xd18c5d in _ZL19FinalizeTypedArenasI8JSStringEbPN2js6FreeOpEPPNS1_2gc11ArenaHeaderERNS4_9ArenaListENS4_9AllocKindERNS1_11SliceBudgetE /srv/repos/mozilla-central/js/src/jsgc.cpp:540
    #3 0xec61f6 in js::gc::ArenaLists::backgroundFinalize(js::FreeOp*, js::gc::ArenaHeader*, bool) /srv/repos/mozilla-central/js/src/jsgc.cpp:1539
    #4 0xebbaf7 in GCCycle(JSRuntime*, bool, long, js::JSGCInvocationKind, JS::gcreason::Reason) /srv/repos/mozilla-central/js/src/jsgc.cpp:4786
previously allocated by thread T0 here:
    #0 0x4c6995 in __interceptor_malloc _asan_rtl_
    #1 0xeeed65 in js_malloc(unsigned long) /srv/repos/mozilla-central/js/src/opt64asan/js/src/../../dist/include/js/Utility.h:144
    #2 0x4ff625 in FileAsString(JSContext*, char const*) /srv/repos/mozilla-central/js/src/shell/js.cpp:1104
    #3 0x4f61a0 in Run(JSContext*, unsigned int, JS::Value*) /srv/repos/mozilla-central/js/src/shell/js.cpp:1176
    #4 0xf8eb1b in JSFunction::native() const /srv/repos/mozilla-central/js/src/jscntxtinlines.h:220
    #5 0xf377c8 in js::Invoke(JSContext*, JS::Value const&, JS::Value const&, unsigned int, JS::Value*, JS::MutableHandle<JS::Value>) /srv/repos/mozilla-central/js/src/vm/Interpreter.cpp:521
    #6 0x82e98a in js::jit::DoCallFallback(JSContext*, js::jit::BaselineFrame*, js::jit::ICCall_Fallback*, unsigned int, JS::Value*, JS::MutableHandle<JS::Value>) /srv/repos/mozilla-central/js/src/jit/BaselineIC.cpp:8103
    #7 0x7fd76b2b1323 in
    #8 0x61100032da17 in
    #9 0x7fd76b2aa503 in
Shadow bytes around the buggy address:
  0x0ffb6cd804b0: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x0ffb6cd804c0: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x0ffb6cd804d0: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x0ffb6cd804e0: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
  0x0ffb6cd804f0: fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa fa
=>0x0ffb6cd80500:[fd]fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x0ffb6cd80510: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x0ffb6cd80520: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x0ffb6cd80530: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x0ffb6cd80540: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
  0x0ffb6cd80550: fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd fd
Shadow byte legend (one shadow byte represents 8 application bytes):
  Addressable:           00
  Partially addressable: 01 02 03 04 05 06 07
  Heap left redzone:     fa
  Heap right redzone:    fb
  Freed heap region:     fd
  Stack left redzone:    f1
  Stack mid redzone:     f2
  Stack right redzone:   f3
  Stack partial redzone: f4
  Stack after return:    f5
  Stack use after scope: f8
  Global redzone:        f9
  Global init order:     f6
  Poisoned by user:      f7
  ASan internal:         fe
==19462==ABORTING
"""  # noqa

asanTraceInvalidFree = """
==30731==ERROR: AddressSanitizer: attempting free on address which was not malloc()-ed: 0x62a00006c200 in thread T24 (MediaPD~oder #1)
    #0 0x4c8690 in __interceptor_free /srv/repos/llvm/projects/compiler-rt/lib/asan/asan_malloc_linux.cc:38
"""  # noqa

asanTraceDebugAssertion = """
### XPCOM_MEM_LEAK_LOG defined -- logging leaks to wtmp1/q1-final-leaks.txt
Crash Annotation GraphicsCriticalError: |[0][GFX1]: Texture deallocated too late during shutdown (t=22.4895) [GFX1]: Texture deallocated too late during shutdown
Assertion failure: false (An assert from the graphics logger), at /builds/slave/m-cen-l64-asan-d-0000000000000/build/src/gfx/2d/Logging.h:521
#01: nsCycleCollector::CollectWhite() (/builds/slave/m-cen-l64-asan-d-0000000000000/build/src/xpcom/base/nsCycleCollector.cpp:3347)
#02: nsCycleCollector::Collect(ccType, js::SliceBudget&, nsICycleCollectorListener*, bool) (/builds/slave/m-cen-l64-asan-d-0000000000000/build/src/xpcom/base/nsCycleCollector.cpp:3692)
#03: nsCycleCollector::ShutdownCollect() (/builds/slave/m-cen-l64-asan-d-0000000000000/build/src/xpcom/base/nsCycleCollector.cpp:3609)
#04: nsCycleCollector_shutdown() (/builds/slave/m-cen-l64-asan-d-0000000000000/build/src/xpcom/base/nsCycleCollector.cpp:4219)
#05: mozilla::ShutdownXPCOM(nsIServiceManager*) (/builds/slave/m-cen-l64-asan-d-0000000000000/build/src/xpcom/build/XPCOMInit.cpp:969)
#06: ScopedXPCOMStartup::~ScopedXPCOMStartup() (/builds/slave/m-cen-l64-asan-d-0000000000000/build/src/toolkit/xre/nsAppRunner.cpp:1474)
#07: operator delete(void*) (/builds/slave/m-cen-l64-asan-d-0000000000000/build/src/obj-firefox/dist/include/mozilla/mozalloc.h:217)
#08: mozilla::UniquePtr<ScopedXPCOMStartup, mozilla::DefaultDelete<ScopedXPCOMStartup> >::operator=(decltype(nullptr)) (/builds/slave/m-cen-l64-asan-d-0000000000000/build/src/obj-firefox/dist/include/mozilla/UniquePtr.h:314)
ASAN:SIGSEGV
=================================================================
==17560==ERROR: AddressSanitizer: SEGV on unknown address 0x000000000000 (pc 0x7f04990c1f2c sp 0x7ffef0e38f60 bp 0x7ffef0e38f70 T0)
    #0 0x7f0497771ea5 in nsCycleCollector::CollectWhite() /builds/slave/m-cen-l64-asan-d-0000000000000/build/src/xpcom/base/nsCycleCollector.cpp:3345
    #1 0x7f0497774498 in nsCycleCollector::Collect(ccType, js::SliceBudget&, nsICycleCollectorListener*, bool) /builds/slave/m-cen-l64-asan-d-0000000000000/build/src/xpcom/base/nsCycleCollector.cpp:3691
    #2 0x7f0497774064 in nsCycleCollector::ShutdownCollect() /builds/slave/m-cen-l64-asan-d-0000000000000/build/src/xpcom/base/nsCycleCollector.cpp:3609
    #3 0x7f0497777c45 in nsCycleCollector_shutdown() /builds/slave/m-cen-l64-asan-d-0000000000000/build/src/xpcom/base/nsCycleCollector.cpp:4219
    #4 0x7f04978e0347 in mozilla::ShutdownXPCOM(nsIServiceManager*) /builds/slave/m-cen-l64-asan-d-0000000000000/build/src/xpcom/build/XPCOMInit.cpp:967
    #5 0x7f049dfe3f7a in ScopedXPCOMStartup::~ScopedXPCOMStartup() /builds/slave/m-cen-l64-asan-d-0000000000000/build/src/toolkit/xre/nsAppRunner.cpp:1473
    #6 0x7f049dff0b55 in mozilla::DefaultDelete<ScopedXPCOMStartup>::operator()(ScopedXPCOMStartup*) const /builds/slave/m-cen-l64-asan-d-0000000000000/build/src/obj-firefox/dist/include/mozilla/UniquePtr.h:528
    #7 0x7f049dfeffdf in mozilla::UniquePtr<ScopedXPCOMStartup, mozilla::DefaultDelete<ScopedXPCOMStartup> >::operator=(decltype(nullptr)) /builds/slave/m-cen-l64-asan-d-0000000000000/build/src/obj-firefox/dist/include/mozilla/UniquePtr.h:313

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV /builds/slave/m-cen-l64-asan-d-0000000000000/build/src/obj-firefox/dist/include/mozilla/gfx/Logging.h:524 mozilla::gfx::Log<1, mozilla::gfx::CriticalLogger>::WriteLog(std::string const&)
==17560==ABORTING
"""  # noqa

asanTraceMemcpyParamOverlap = """
==4782==ERROR: AddressSanitizer: memcpy-param-overlap: memory ranges [0x7f47486b18f8,0x7f47486b3904) and [0x7f47486b1800, 0x7f47486b380c) overlap
    #0 0x49b496 in __asan_memcpy /builds/slave/moz-toolchain/src/llvm/projects/compiler-rt/lib/asan/asan_interceptors.cc:393:3
    #1 0x7f47a81e9260 in S32_Opaque_BlitRow32(unsigned int*, unsigned int const*, int, unsigned int) /home/worker/workspace/build/src/gfx/skia/skia/src/core/SkBlitRow_D32.cpp:20:5
"""  # noqa

asanTraceStrcatParamOverlap = """
==12266==ERROR: AddressSanitizer: strcat-param-overlap: memory ranges [0x6210001a0541,0x6210001a054f) and [0x6210001a054c, 0x6210001a0556) overlap
    #0 0x7f5c2db40c40 in __interceptor_strcat /build/gcc/src/gcc/libsanitizer/asan/asan_interceptors.cc:349
"""  # noqa

asanTraceFailedAlloc = """
==18847==ERROR: AddressSanitizer failed to allocate 0x6003a000 (1610850304) bytes of LargeMmapAllocator (error code: 12)
==18847==Process memory map follows:
  0x08048000-0x081d7000 /foo/bar
  0xffb00000-0xffb21000 [stack]
==18847==End of process memory map.
==18847==AddressSanitizer CHECK failed: /build/llvm-toolchain-4.0-euGZ6h/llvm-toolchain-4.0-4.0/projects/compiler-rt/lib/sanitizer_common/sanitizer_common.cc:120 "((0 && "unable to mmap")) != (0)" (0x0, 0x0)
    #0 0x8127526 in __asan::AsanCheckFailed(char const*, int, char const*, unsigned long long, unsigned long long) (build/dump_video+0x8127526)
    #1 0x814262b in __sanitizer::CheckFailed(char const*, int, char const*, unsigned long long, unsigned long long) (build/dump_video+0x814262b)
    #2 0x8131f9a in __sanitizer::ReportMmapFailureAndDie(unsigned long, char const*, char const*, int, bool) (build/dump_video+0x8131f9a)
    #3 0x813b0ef in __sanitizer::MmapOrDie(unsigned long, char const*, bool) (build/dump_video+0x813b0ef)
    #4 0x8069ec9 in __asan::Allocator::Allocate(unsigned long, unsigned long, __sanitizer::BufferedStackTrace*, __asan::AllocType, bool) (build/dump_video+0x8069ec9)
    #5 0x80657f6 in __asan::asan_malloc(unsigned long, __sanitizer::BufferedStackTrace*) (build/dump_video+0x80657f6)
    #6 0x811c181 in __interceptor_malloc (build/dump_video+0x811c181)
    #7 0x817999f in oc_state_frarray_init lib/state.c:506:24
    #8 0x817999f in oc_state_init lib/state.c:735
    #9 0x815ab3c in oc_dec_init lib/decode.c:374:7
    #10 0xf74f5636 in __libc_start_main (/lib32/libc.so.6+0x18636)
    #11 0x80609b7 in _start (build/dump_video+0x80609b7)
"""  # noqa

asanTraceAllocSize = """
==11096==ERROR: AddressSanitizer: requested allocation size 0x7ff9cdc82cb0 (0x7ff9cdc83cb0 after adjustments for alignment, red zones etc.) exceeds maximum supported size of 0x10000000000 (thread T0)
    #0 0x7ffa032145d0 in malloc Z:\\compiler-rt\\lib\\asan\\asan_malloc_win.cc:69
"""  # noqa

asanMultiTrace = """
=================================================================
==8746==ERROR: AddressSanitizer: SEGV on unknown address 0x7f637b59cffc (pc 0x7f63fd5c11af bp 0x7f63a0702090 sp 0x7f63a0701f40 T35)
Done, waiting 10ms before calling close()
    #0 0x7f63fd5c11ae in mozilla::ipc::Shmem::OpenExisting(mozilla::ipc::Shmem::IHadBetterBeIPDLCodeCallingThis_OtherwiseIAmADoodyhead, IPC::Message const&, int*, bool) /home/worker/workspace/build/src/ipc/glue/Shmem.cpp:454:35
    #1 0x7f63fd5c07b0 in mozilla::ipc::IToplevelProtocol::ShmemCreated(IPC::Message const&) /home/worker/workspace/build/src/ipc/glue/ProtocolUtils.cpp:790:38

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV /home/worker/workspace/build/src/ipc/glue/Shmem.cpp:454:35 in mozilla::ipc::Shmem::OpenExisting(mozilla::ipc::Shmem::IHadBetterBeIPDLCodeCallingThis_OtherwiseIAmADoodyhead, IPC::Message const&, int*, bool)
Thread T35 (Compositor) created by T0 here:
    #0 0x4a8e16 in __interceptor_pthread_create /builds/slave/moz-toolchain/src/llvm/projects/compiler-rt/lib/asan/asan_interceptors.cc:245:3
    #1 0x7f63fd4d9ad4 in CreateThread /home/worker/workspace/build/src/ipc/chromium/src/base/platform_thread_posix.cc:139:14

==8746==ABORTING
ASAN:DEADLYSIGNAL
=================================================================
ASAN:DEADLYSIGNAL
=================================================================
==8986==ERROR: AddressSanitizer: SEGV on unknown address 0x000000000000 (pc 0x7fcfcfaadeda bp 0x7fcfcb405340 sp 0x7fcfcb405320 T2)
==8986==The signal is caused by a WRITE memory access.
==8927==ERROR: AddressSanitizer: SEGV on unknown address 0x000000000000 (pc 0x7f2fc08adeda bp 0x7f2fbc21c340 sp 0x7f2fbc21c320 T2)
==8986==Hint: address points to the zero page.
==8927==The signal is caused by a WRITE memory access.
==8927==Hint: address points to the zero page.
Crash Annotation GraphicsCriticalError: |[C0][GFX1-]: Receive IPC close with reason=AbnormalShutdown (t=72.7299)
###!!! [Child][MessageChannel::SendAndWait] Error: Channel error: cannot send/recv
"""  # noqa

asanTruncatedTrace = """
==8986==ERROR: AddressSanitizer: SEGV on unknown address 0x000000000000 (pc 0x7fcfcfaadeda bp 0x7fcfcb405340 sp 0x7fcfcb405320 T2)
==8986==The signal is caused by a WRITE memory access.
"""  # noqa

gdbCrashAddress1 = """
(gdb) bt 16
#0  js::types::TypeObject::addProperty (this=0xf7469400, cx=0x9366458, id=$jsid(0x0), pprop=0xf7469418) at /srv/repos/mozilla-central/js/src/jsinfer.cpp:3691
(More stack frames follow...)
(gdb) info reg
eax            0x1      1
ecx            0x1      1
(gdb) x /i $pc
=> 0x812bf19 <js::types::TypeObject::addProperty(JSContext*, jsid, js::types::Property**)+121>: mov    (%ecx),%ecx
"""  # noqa

gdbCrashAddress2 = """
Program terminated with signal 11, Segmentation fault.
#0  repoint (this=0x160fc30, cx=0x15a4940, masm=..., attacher=..., ion=0x160fa80, attachKind=0x2b08c0 \"generic\") at /srv/repos/mozilla-central/js/src/ion/IonCaches.cpp:44
#1  CodeLocationJump (this=0x160fc30, cx=0x15a4940, masm=..., attacher=..., ion=0x160fa80, attachKind=0x2b08c0 \"generic\") at ../ion/shared/Assembler-shared.h:452
r0      0x34    52
r4      0x15a4940       22694208
r10     0x0     0
sp      0xbe9fec08      3198151688
pc      0x1a03ae <js::ion::IonCache::linkAndAttachStub(JSContext*, js::ion::MacroAssembler&, js::ion::IonCache::StubAttacher&, js::ion::IonScript*, char const*)+122>
cpsr    0xd0030 852016
=> 0x1a03ae <js::ion::IonCache::linkAndAttachStub(JSContext*, js::ion::MacroAssembler&, js::ion::IonCache::StubAttacher&, js::ion::IonScript*, char const*)+122>:       ldr.w   r4, [r10]
   0x1a03b2 <js::ion::IonCache::linkAndAttachStub(JSContext*, js::ion::MacroAssembler&, js::ion::IonCache::StubAttacher&, js::ion::IonScript*, char const*)+126>:       mov     r3, r0
"""  # noqa

gdbCrashAddress3 = """
(gdb) bt 16
#0  js::types::TypeObject::addProperty (this=0xf7469400, cx=0x9366458, id=$jsid(0x0), pprop=0xf7469418) at /srv/repos/mozilla-central/js/src/jsinfer.cpp:3691
(More stack frames follow...)
(gdb) info reg
rax            0x1      1
rdx            0x1      1
rbx            0x1      1
(gdb) x /i $pc
=> 0x812bf19 <js::types::TypeObject::addProperty(JSContext*, jsid, js::types::Property**)+121>: shrb   -0x69(%rdx,%rbx,8)
"""  # noqa

gdbCrashAddress4 = """
received signal SIGILL, Illegal instruction.
0x000008ab336edd14 in ?? ()
#0  0x000008ab336edd14 in ?? ()
#1  0x0000000000554ac4 in Interpret (cx=0xffffffffcc20, state=...) at js/src/vm/Interpreter.cpp:2037
x0	0x1	1
sp	0xffffc780	281474976696192
pc	0x3ef29d14	20513819893012
cpsr	0x0	0
fpcsr	void
fpcr	0x0	0
=> 0x8ab336edd14:	.inst	0xffff006c ; undefined
"""  # noqa

gdbCrashAddress5 = """
Program terminated with signal SIGSEGV, Segmentation fault.
#0  0x0000000000b49798 in js::gc::TenuredCell::arena (this=<optimized out>) at /home/ubuntu/mozilla-central/js/src/gc/Cell.h:333
x0	0x9f3f1da0	281473353457056
x1	0x1d9540	7696583333184
x2	0x87afa000	281472958177280
sp	0xa0065000	281473366511616
pc	0xb49798 <IsAboutToBeFinalizedInternal<JSObject>(JSObject**)+56>
cpsr	0x20000000	536870912
fpcsr	void
fpcr	0x0	0
=> 0xb49798 <IsAboutToBeFinalizedInternal<JSObject>(JSObject**)+56>:	ldrb	w2, [x2,#20]
"""  # noqa

gdbSampleTrace1 = """
[New Thread 14711]
[Thread debugging using libthread_db enabled]
Core was generated by `/srv/repos/ionmonkey/js/src/opt32/js --ion -n -m --ion-eager -f /home/ownhero/h'.
Program terminated with signal 11, Segmentation fault.
#0  0x083fa060 in internalAppend<js::ion::MDefinition*> (this=0x847e4e8, ins=0x9e2ced0) at ./dist/include/js/Vector.h:790
790         new(endNoCheck()) T(t);
#0  0x083fa060 in internalAppend<js::ion::MDefinition*> (this=0x847e4e8, ins=0x9e2ced0) at ./dist/include/js/Vector.h:790
#1  append<js::ion::MDefinition*> (this=0x847e4e8, ins=0x9e2ced0) at ./dist/include/js/Vector.h:779
#2  js::ion::MPhi::addInput (this=0x847e4e8, ins=0x9e2ced0) at /home/ownhero/homes/mozilla/repos/ionmonkey/js/src/ion/MIR.cpp:456
#3  0x0838ad1c in js::ion::MBasicBlock::setBackedge (this=0x9d4a630, pred=0x9e2d0a8) at /home/ownhero/homes/mozilla/repos/ionmonkey/js/src/ion/MIRGraph.cpp:661
#4  0x0833ea08 in js::ion::IonBuilder::finishLoop (this=0xffdef8e0, state=..., successor=0x9e2d280) at /home/ownhero/homes/mozilla/repos/ionmonkey/js/src/ion/IonBuilder.cpp:1303
#5  0x0833eb47 in js::ion::IonBuilder::processForUpdateEnd (this=0xffdef8e0, state=...) at /home/ownhero/homes/mozilla/repos/ionmonkey/js/src/ion/IonBuilder.cpp:1476
#6  0x08350ac0 in processCfgStack (this=0xffdef8e0) at /home/ownhero/homes/mozilla/repos/ionmonkey/js/src/ion/IonBuilder.cpp:1104
#7  js::ion::IonBuilder::traverseBytecode (this=0xffdef8e0) at /home/ownhero/homes/mozilla/repos/ionmonkey/js/src/ion/IonBuilder.cpp:627
eax    0x0    0
ebx    0x8962ff4    144060404
ecx    0xf76038ac    -144688980
edx    0x0    0
esi    0xf7602d9c    -144691812
edi    0x0    0
ebp    0xff916fb8    4287721400
esp    0xff916ed0    4287721168
eip    0x818bc33 <js::InvokeKernel(JSContext*, JS::CallArgs, js::MaybeConstruct)+419>
=> 0x818bc33 <js::InvokeKernel(JSContext*, JS::CallArgs, js::MaybeConstruct)+419>:    movl   $0x7b,0x0
   0x818bc3d <js::InvokeKernel(JSContext*, JS::CallArgs, js::MaybeConstruct)+429>:    call   0x804af50 <abort@plt>
"""  # noqa

gdbSampleTrace2 = """
Program terminated with signal 11, Segmentation fault.
#0  operator+ (this=0xf6c7e760, cx=0xa3024b8, iv=..., useLocale=false, buffer=..., sb=...) at ../gc/Barrier.h:462
462         HeapSlotArray operator +(uint32_t offset) const { return HeapSlotArray(array + offset); }
#0  operator+ (this=0xf6c7e760, cx=0xa3024b8, iv=..., useLocale=false, buffer=..., sb=...) at ../gc/Barrier.h:462
#1  js::ParallelArrayObject::toStringBufferImpl (this=0xf6c7e760, cx=0xa3024b8, iv=..., useLocale=false, buffer=..., sb=...) at /srv/repos/mozilla-central/js/src/builtin/ParallelArray.cpp:1521
#2  0x081d0379 in js::ParallelArrayObject::toStringBuffer (this=0xf6c7e760, cx=0xa3024b8, useLocale=false, sb=...) at /srv/repos/mozilla-central/js/src/builtin/ParallelArray.cpp:1566
#3  0x081d05b3 in js::ParallelArrayObject::toString (cx=0xa3024b8, args=...) at /srv/repos/mozilla-central/js/src/builtin/ParallelArray.cpp:1573
#4  0x081d06be in CallNonGenericMethod (cx=0xa3024b8, argc=0, vp=0xf6ee2150) at ../jsapi.h:1570
#5  NonGenericMethod<js::ParallelArrayObject::toString> (cx=0xa3024b8, argc=0, vp=0xf6ee2150) at /srv/repos/mozilla-central/js/src/builtin/ParallelArray.cpp:163
#6  0x080d8dd8 in CallJSNative (cx=0xa3024b8, args=..., construct=js::NO_CONSTRUCT) at ../jscntxtinlines.h:389
#7  PropertyAccess<(PropertyAccessKind)1> (cx=0xa3024b8, args=..., construct=js::NO_CONSTRUCT) at /srv/repos/mozilla-central/js/src/jsinterp.cpp:351
rbx            0x1      1
r14            0x1      1
=> 0x7f01fffecf41:    mov    0x8(%r14),%rbx
   0x7f01fffecf45:    cmp    %rbx,0x18(%rdi)
"""  # noqa

gdbSampleTrace3 = """
Program terminated with signal 11, Segmentation fault.
#0  0x083ba5a9 in AssertCanGC () at /srv/repos/ionmonkey/js/src/gc/Root.h:1029
1029        JS_ASSERT_IF(isGCEnabled(), !InNoGCScope());
#0  0x083ba5a9 in AssertCanGC () at /srv/repos/ionmonkey/js/src/gc/Root.h:1029
#1  js::gc::NewGCThing<JSString, (js::AllowGC)1> (cx=0x9224850, kind=js::gc::FINALIZE_STRING, thingSize=16, heap=js::gc::TenuredHeap) at ../jsgcinlines.h:491
#2  0x083b205d in js_NewGCString<(js::AllowGC)1> (cx=0x9224850) at ../jsgcinlines.h:578
#3  0x08508069 in new_<(js::AllowGC)1> (length=33, right=\"result: \", left=\"\\njstest: undefined bug:  \", cx=0x9224850) at /srv/repos/ionmonkey/js/src/vm/String-inl.h:194
#4  js::ConcatStrings<(js::AllowGC)1> (cx=0x9224850,: left=\"\\njstest: undefined bug:  \", right=\"result: \") at /srv/repos/ionmonkey/js/src/vm/String.cpp:339
#5  0x08780467 in js::ion::DoConcatStrings (cx=0x9224850, lhs=$jsval(-nan(0xfff85f6bb4ff0)), rhs=$jsval(-nan(0xfff85f6c194e0)), res=$jsval(-nan(0xfff8200000000))) at /srv/repos/ionmonkey/js/src/ion/BaselineIC.cpp:2037
#6  0xf772685f in ?? ()
#7  0xf772bb76 in ?? ()
"""  # noqa

gdbRegressionTrace1 = """
Program received signal SIGSEGV, Segmentation fault.
js::ScriptedIndirectProxyHandler::defineProperty (this=0x930fad4, cx=0x9339130, proxy=(JSObject * const) 0xf6700050 [object Array], id=$jsid(0), desc={obj = (JSObject *) 0xf6247040 [object Proxy], attrs = 61524, getter = 0xf6700120, setter = 0, value = $jsval(-nan(0xfff88f62460d0))}) at /srv/repos/mozilla-central/js/src/proxy/ScriptedIndirectProxyHandler.cpp:201
201         RootedObject handler(cx, GetIndirectProxyHandlerObject(proxy));
#0  js::ScriptedIndirectProxyHandler::defineProperty (this=0x930fad4, cx=0x9339130, proxy=(JSObject * const) 0xf6700050 [object Array], id=$jsid(0), desc={obj = (JSObject *) 0xf6247040 [object Proxy], attrs = 61524, getter = 0xf6700120, setter = 0, value = $jsval(-nan(0xfff88f62460d0))}) at /srv/repos/mozilla-central/js/src/proxy/ScriptedIndirectProxyHandler.cpp:201
#1  0x084ac820 in js::SetPropertyIgnoringNamedGetter (cx=0x9339130, handler=0x930fad4, proxy=(JSObject * const) 0xf6247040 [object Proxy], receiver=(JSObject * const) 0xf6700050 [object Array], id=$jsid(0), desc={obj = (JSObject *) 0xf6247040 [object Proxy], attrs = 61524, getter = 0xf6700120, setter = 0, value = $jsval(-nan(0xfff88f62460d0))}, descIsOwn=true, strict=false, vp=$jsval(-nan(0xfff88f62460d0))) at /srv/repos/mozilla-central/js/src/proxy/BaseProxyHandler.cpp:186
#2  0x084b0677 in js::ScriptedIndirectProxyHandler::derivedSet (this=0x930fad4, cx=0x9339130, proxy=(JSObject * const) 0xf6247040 [object Proxy], receiver=(JSObject * const) 0xf6700050 [object Array], id=$jsid(0), strict=false, vp=$jsval(-nan(0xfff88f62460d0))) at /srv/repos/mozilla-central/js/src/proxy/ScriptedIndirectProxyHandler.cpp:311
#3  0x084b08a8 in js::ScriptedIndirectProxyHandler::set (this=0x930fad4, cx=0x9339130, proxy=(JSObject * const) 0xf6247040 [object Proxy], receiver=(JSObject * const) 0xf6700050 [object Array], id=$jsid(0), strict=false, vp=$jsval(-nan(0xfff88f62460d0))) at /srv/repos/mozilla-central/js/src/proxy/ScriptedIndirectProxyHandler.cpp:290
#4  0x084aeb59 in js::Proxy::set (cx=0x9339130, proxy=(JSObject * const) 0xf6247040 [object Proxy], receiver=(JSObject * const) 0xf6700050 [object Array], id=$jsid(0), strict=false, vp=$jsval(-nan(0xfff88f62460d0))) at /srv/repos/mozilla-central/js/src/proxy/Proxy.cpp:336
#5  0x08535ec0 in setGeneric (strict=<optimized out>, vp=..., id=..., receiver=..., obj=(JSObject * const) 0xf6247040 [object Proxy], cx=0x9339130) at /srv/repos/mozilla-central/js/src/vm/NativeObject.h:1428
#6  js::baseops::SetPropertyHelper<(js::ExecutionMode)0> (cxArg=0x9339130, obj=(js::NativeObject * const) 0xf6700050 [object Array], receiver=(JSObject * const) 0xf6700050 [object Array], id=$jsid(0), qualified=js::baseops::Qualified, vp=$jsval(-nan(0xfff88f62460d0)), strict=false) at /srv/repos/mozilla-central/js/src/vm/NativeObject.cpp:2353
#7  0x08519490 in setGeneric (strict=false, vp=..., id=..., receiver=..., obj=(JSObject * const) 0xf6700050 [object Array], cx=0x9339130) at /srv/repos/mozilla-central/js/src/vm/NativeObject.h:1430
"""  # noqa

gdbRegressionTrace2 = """
Program received signal SIGSEGV, Segmentation fault.
0xf7673132 in ?? ()
#0  0xf7673132 in ?? ()
eax            0xf6043040    -167497664
ecx            0xf651f4b0    -162401104
edx            0xf651f4d0    -162401072
ebx            0xf651f4f0    -162401040
esp            0xfffd573c    0xfffd573c
ebp            0xfffd57e4    0xfffd57e4
esi            0x0    0
edi            0x934d3d0    154457040
eip            0xf7673132    0xf7673132
=> 0xf7673132:    vmovaps %xmm1,0x60(%esp)
"""

gdbRegressionTrace3 = """
Program received signal SIGTRAP, Trace/breakpoint trap.
0x00007ffff5573368 in ?? ()
#0  0x00007ffff5573368 in ?? ()
#1  0x00007ffff558a9c9 in ?? ()
#2  0x0000000000000183 in ?? ()
#3  0x00007ffff5671ac0 in ?? ()
#4  0x0000000000000000 in ?? ()
rax    0x1ac4d40    28069184
rbx    0x7ffff5658730    140737310459696
rcx    0xfff9000000000000    -1970324836974592
rdx    0xfffc7ffff5700060    -985162595696544
rsi    0x7ffff55efa4d    140737310030413
rdi    0x1acfa60    28113504
rbp    0x7fffffffbf20    140737488338720
rsp    0x7fffffffbf28    140737488338728
r8    0x7ffff565b060    140737310470240
r9    0x0    0
r10    0x0    0
r11    0x7ffff6c3fc90    140737333427344
r12    0x0    0
r13    0x7fffffffca00    140737488341504
r14    0x183    387
r15    0x7ffff558a970    140737309616496
rip    0x7ffff5573368    140737309520744
=> 0x7ffff5573368:    movabs $0x7fffffffffff,%rbx
   0x7ffff5573372:    and    0xa08(%rax),%rbx
"""

gdbRegressionTrace4 = """
Program received signal SIGSEGV, Segmentation fault.
0x0000000000000000 in ?? ()
#0  0x0000000000000000 in ?? ()
#1 0xfffc7ffff7e8a6c0 in ?? ()
#2 0x000000000043026c in js::jit::IonCompile (cx=0xfffc7ffff7e766c0, script=<optimized out>, baselineFrame=<optimized out>, osrPc=<optimized out>, constructing=<optimized out>, recompile=<optimized out>, optimizationLevel=js::jit::Optimization_DontCompile) at /home/ownhero/homes/mozilla/repos/mozilla-central/js/src/jit/Ion.cpp:2253
#3 0x00007ffff7e61160 in ?? ()
#4 0x0000000000000000 in ?? ()
rax    0x0    0
rbx    0xfffc7ffff7e766c0    -985162554317120
rcx    0x7fffffffd6c0    140737488344768
rdx    0x7ffff6907050    140737330049104
rsi    0x0    0
rdi    0x7ffff6a00048    140737331069000
rbp    0x7fffffffd270    140737488343664
rsp    0x7fffffffd240    140737488343616
r8    0x0    0
r9    0xffffc000    4294950912
r10    0x46000    286720
r11    0x7ffff6a00121    140737331069217
r12    0x8    8
r13    0x7fffffffd6f0    140737488344816
r14    0x1    1
r15    0x7ffff6914800    140737330104320
rip    0x0    0
=> 0x0: """  # noqa

gdbRegressionTrace5 = """
Program received signal SIGSEGV, Segmentation fault.
0xf7673132 in ?? ()
#0  0xf7673132 in ?? ()
eax            0xf6043040    -167497664
ecx            0xf651f4b0    -162401104
edx            0xf651f4d0    -162401072
ebx            0xf651f4f0    -162401040
esp            0xfffd573c    0xfffd573c
ebp            0xfffd57e4    0xfffd57e4
esi            0x0    0
edi            0x934d3d0    154457040
eip            0xf7673132    0xf7673132
=> 0xf7673132:    ret
"""

gdbRegressionTrace6 = """
Program received signal SIGSEGV, Segmentation fault.
0xf7673132 in ?? ()
#0  0xf7673132 in ?? ()
eax            0xf6043040    -167497664
ecx            0xf651f4b0    -162401104
edx            0xf651f4d0    -162401072
ebx            0xf651f4f0    -162401040
esp            0xfffd573c    0xfffd573c
ebp            0xfffd57e4    0xfffd57e4
esi            0x0    0
edi            0x934d3d0    154457040
eip            0xf7673132    0xf7673132
=> 0xf7673132:    ud2
"""

gdbRegressionTrace7 = """
Assertion failure: this->is<T>(), at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/jsobj.h:554

Thread 1 "js" received signal SIGSEGV, Segmentation fault.
0x0000000000b7e884 in JSObject::as<js::ModuleEnvironmentObject> (this=<optimized out>) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/jsobj.h:554
554     /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/jsobj.h: No such file or directory.
#0  0x0000000000b7e884 in JSObject::as<js::ModuleEnvironmentObject> (this=<optimized out>) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/jsobj.h:554
#1  0x0000000000b4b041 in js::ScopeIter::settle (this=this@entry=0x7fffffffaea0) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/vm/ScopeObject.cpp:1481
#2  0x0000000000b4b653 in js::ScopeIter::ScopeIter(JSContext*, js::AbstractFramePtr, unsigned char*, mozilla::detail::GuardObjectNotifier&&) (this=0x7fffffffaea0, cx=0x7ffff691ac00, frame=..., pc=<optimized out>, _notifier=<unknown type in /home/decoder/LangFuzz/work/remote/builds/debug64/dist/bin/js, CU 0x400acc3, DIE 0x41cf0a6>) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/vm/ScopeObject.cpp:1413
#3  0x0000000000834eec in js::jit::DebugEpilogue (cx=cx@entry=0x7ffff691ac00, frame=frame@entry=0x7fffffffb668, pc=0x7ffff69f4e96 "0", ok=<optimized out>) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/jit/VMFunctions.cpp:707
#4  0x000000000071a505 in js::jit::OnLeaveBaselineFrame (frameOk=<optimized out>, rfe=0x7fffffffb5d0, pc=<optimized out>, frame=..., cx=0x7ffff691ac00) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/jit/JitFrames.cpp:463
#5  js::jit::HandleExceptionBaseline (pc=0x7ffff69f4e96 "0", rfe=<optimized out>, frame=..., cx=0x7ffff691ac00) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/jit/JitFrames.cpp:696
#6  js::jit::HandleException (rfe=<optimized out>) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/jit/JitFrames.cpp:837
#7  0x00007ffff7fe6608 in ?? ()
#8  0x0000000000000000 in ?? ()
rax     0x0     0
rbx     0x7fffffffaea0  140737488334496
rcx     0x7ffff6c28a2d  140737333332525
rdx     0x0     0
rsi     0x7ffff6ef7770  140737336276848
rdi     0x7ffff6ef6540  140737336272192
rbp     0x7fffffffadb0  140737488334256
rsp     0x7fffffffadb0  140737488334256
r8      0x7ffff6ef7770  140737336276848
r9      0x7ffff7fdc740  140737353992000
r10     0x0     0
r11     0x0     0
r12     0x7ffff7e7b100  140737352544512
r13     0x7ffff7e7b100  140737352544512
r14     0x7fffffffae00  140737488334336
r15     0x7fffffffadf0  140737488334320
rip     0xb7e884 <JSObject::as<js::ModuleEnvironmentObject>()+52>
=> 0xb7e884 <JSObject::as<js::ModuleEnvironmentObject>()+52>:   movl   $0x0,0x0
   0xb7e88f <JSObject::as<js::ModuleEnvironmentObject>()+63>:   ud2
A debugging session is active.

        Inferior 1 [process 24244] will be killed.
"""  # noqa

gdbRegressionTrace8 = """
Program terminated with signal SIGSEGV, Segmentation fault.
#0  0x0814977d in js::Mutex::lock (this=0xf7123988) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/threading/posix/Mutex.cpp:65
#1  0x0848d094 in js::LockGuard<js::Mutex>::LockGuard (aLock=..., this=<synthetic pointer>) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/threading/LockGuard.h:25
#2  js::jit::AutoLockSimulatorCache::AutoLockSimulatorCache (sim=0xf7123000, this=<synthetic pointer>) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/jit/arm/Simulator-arm.cpp:369
#3 <signal handler called>
#4 0xf7442cfc in ?? () from /lib32/libc.so.6
#5 0x08488e62 in js::jit::CheckICacheLocked (instr=0xf49d1648, i_cache=...) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/jit/arm/Simulator-arm.cpp:1034
"""  # noqa

gdbRegressionTrace9 = """
Program terminated with signal SIGSEGV, Segmentation fault.
#0  0x083c4a4b in js::ToPrimitiveSlow (cx=0xf7152000, preferredType=JSTYPE_NUMBER, vp=...) at js/src/jsobj.cpp:3084
#1  0x083d2f59 in js::ToPrimitive (vp=..., preferredType=JSTYPE_NUMBER, cx=<optimized out>) at js/src/jsobj.h:1062
eax            0xffe0104c       -2092980
ecx            0xffe01058       -2092968
edx            0xffe01050       -2092976
ebx            0x8950ff4        143986676
esp            0xffe01000       0xffe01000
ebp            0xffe010c8       0xffe010c8
esi            0xf7152000       -149610496
edi            0xffe01040       -2092992
eip            0x83c4a4b        0x83c4a4b <js::ToPrimitiveSlow(JSContext*, JSType, JS::MutableHandle<JS::Value>)+219>
=> 0x83c4a4b <js::ToPrimitiveSlow(JSContext*, JSType, JS::MutableHandle<JS::Value>)+219>:       call   0x8120ca0 <js::GetProperty(JSContext*, JS::Handle<JSObject*>, JS::Handle<JSObject*>, JS::Handle<jsid>, JS::MutableHandle<JS::Value>)>
"""  # noqa

gdbRegressionTrace10 = """
Thread 1 received signal SIGILL, Illegal instruction.
0x00007ff7f20c1f81 in ?? ()
=> 0x7ff7f20c1f81:      (bad)
rax            0x55555598e9bd   93824996665789
rbx            0x2fa    762
rcx            0x1      1
rdx            0x4000000000000  1125899906842624
rsi            0x2fa    762
rdi            0x7fffffffbfb0   140737488338864
rbp            0x7fffffffb620   0x7fffffffb620
rsp            0x7fffffffb5c0   0x7fffffffb5c0
r8             0x7fffffffb680   140737488336512
r9             0x5555564fc220   93825008648736
r10            0x0      0
r11            0x555555b9ca90   93824998820496
r12            0x7ffff7e124c0   140737352115392
r13            0x7fffffffb680   140737488336512
r14            0x7fffffffbfb0   140737488338864
r15            0x0      0
rip            0x7ff7f20c1f81   0x7ff7f20c1f81
"""

gdbRegressionTrace11 = """
Program terminated with signal SIGSEGV, Segmentation fault.
0x00007ff7f20c1f81 in ?? ()
rax            0x7ff7f2090f8a   93824996665789
rbx            0x2fa    762
rcx            0x1      1
rdx            0x4000000000000  1125899906842624
rsi            0x2fa    762
rdi            0x7fffffffbfb0   140737488338864
rbp            0x7fffffffb620   0x7fffffffb620
rsp            0x7fffffffb5c0   0x7fffffffb5c0
r8             0x7fffffffb680   140737488336512
r9             0x5555564fc220   93825008648736
r10            0x0      0
r11            0x555555b9ca90   93824998820496
r12            0x7ffff7e124c0   140737352115392
r13            0x7fffffffb680   140737488336512
r14            0x7fffffffbfb0   140737488338864
r15            0x0      0
rip            0x7ff7f20c1f81   0x7ff7f20c1f81
=> 0x83c4a4b <js::ToPrimitiveSlow(JSContext*, JSType, JS::MutableHandle<JS::Value>)+219>:       callq  *0xa8(%rax)
"""

gdbRegressionTrace12 = """
Program terminated with signal SIGSEGV, Segmentation fault.
#0  0x0000000000bf9000 in js::SavedStacks::insertFrames(JSContext*, js::FrameIter&, JS::MutableHandle<js::SavedFrame*>, mozilla::Variant<JS::AllFrames, JS::MaxFrames, JS::FirstSubsumedFrame>&&) (this=this@entry=0x7fc3c234e100, cx=cx@entry=0x7fc3c2316000, iter=..., frame=..., capture=capture@entry=<unknown type in /home/ubuntu/build/dist/bin/js, CU 0x569a418, DIE 0x58e7398>) at js/src/vm/SavedStacks.cpp:1361
#1  0x0000000000bf94c6 in js::SavedStacks::saveCurrentStack(JSContext*, JS::MutableHandle<js::SavedFrame*>, mozilla::Variant<JS::AllFrames, JS::MaxFrames, JS::FirstSubsumedFrame>&&) (this=0x7fc3c234e100, cx=cx@entry=0x7fc3c2316000, frame=..., capture=capture@entry=<unknown type in /home/ubuntu/build/dist/bin/js, CU 0x569a418, DIE 0x58e88cf>) at vm/SavedStacks.cpp:1225
#2  0x00000000009dedfa in JS::CaptureCurrentStack(JSContext*, JS::MutableHandle<JSObject*>, mozilla::Variant<JS::AllFrames, JS::MaxFrames, JS::FirstSubsumedFrame>&&) (cx=0x7fc3c2316000, stackp=..., capture=<unknown type in /home/ubuntu/build/dist/bin/js, CU 0x3d1dbc6, DIE 0x3edf2a4>) at js/src/jsapi.cpp:7755
#3  0x00000000009deedb in CaptureStack (cx=<optimized out>, stack=...) at js/src/jsexn.cpp:369
""" # noqa

gdbRegressionTrace13 = """
received signal SIGSEGV, Segmentation fault.
0x56df6483 in JSScript::global (this=0xe5e5e5e5) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/vm/JSScript-inl.h:149
#0  0x56df6483 in JSScript::global (this=0xe5e5e5e5) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/vm/JSScript-inl.h:149
#1  js::AbstractFramePtr::global (this=0xffffc0bc) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/vm/Stack-inl.h:747
#2  js::Debugger::forEachDebuggerFrame<js::Debugger::inFrameMaps(js::AbstractFramePtr)::<lambda(js::DebuggerFrame*)> >(js::AbstractFramePtr, js::Debugger::<lambda(js::DebuggerFrame*)>) (frame=..., fn=..., fn@entry=...) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/vm/Debugger.cpp:2815
#3  0x56df67d0 in js::Debugger::inFrameMaps (frame=...) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/vm/Debugger.cpp:7164
#4  0x56b1f31a in js::jit::HandleExceptionIon (overrecursed=0xffffc19b, rfe=0xffffc4b8, frame=..., cx=0xf6e1b800) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/jit/JitFrames.cpp:215
#5  js::jit::HandleException (rfe=<optimized out>) at /srv/jenkins/jobs/mozilla-central-clone/workspace/js/src/jit/JitFrames.cpp:710
#6  0xee21eaa3 in ?? ()
Backtrace stopped: previous frame inner to this frame (corrupt stack?)
eax	0xe5e5e5e5	-437918235
ebx	0xec5fd970	-329262736
ecx	0x3	3
edx	0xffffc0bc	-16196
esi	0xf6e1b800	-152979456
edi	0x578beff4	1468788724
ebp	0xffffc0f8	4294951160
esp	0xffffc084	4294951044
eip	0x56df6483 <js::Debugger::forEachDebuggerFrame<js::Debugger::inFrameMaps(js::AbstractFramePtr)::<lambda(js::DebuggerFrame*)> >(js::AbstractFramePtr, js::Debugger::<lambda(js::DebuggerFrame*)>)+67>
=> 0x56df6483 <js::Debugger::forEachDebuggerFrame<js::Debugger::inFrameMaps(js::AbstractFramePtr)::<lambda(js::DebuggerFrame*)> >(js::AbstractFramePtr, js::Debugger::<lambda(js::DebuggerFrame*)>)+67>:	pushl  0x10(%eax)
   0x56df6486 <js::Debugger::forEachDebuggerFrame<js::Debugger::inFrameMaps(js::AbstractFramePtr)::<lambda(js::DebuggerFrame*)> >(js::AbstractFramePtr, js::Debugger::<lambda(js::DebuggerFrame*)>)+70>:	call   0x568893f0 <JS::Realm::maybeGlobal() const>
""" # noqa

rustSampleTrace1 = """
thread 'StyleThread#2' panicked at 'assertion failed: self.get_data().is_some()', /home/worker/workspace/build/src/servo/components/style/gecko/wrapper.rs:976
stack backtrace:
   0: std::sys::imp::backtrace::tracing::imp::unwind_backtrace
   1: std::sys_common::backtrace::_print
   2: std::panicking::default_hook::{{closure}}
   3: std::panicking::default_hook
   4: std::panicking::rust_panic_with_hook
   5: std::panicking::begin_panic
   6: <style::gecko::wrapper::GeckoElement<'le> as style::dom::TElement>::set_dirty_descendants
   7: <style::invalidation::element::invalidator::TreeStyleInvalidator<'a, 'b, E>>::invalidate_child
   8: <style::invalidation::element::invalidator::TreeStyleInvalidator<'a, 'b, E>>::invalidate_dom_descendants_of
   9: <style::invalidation::element::invalidator::TreeStyleInvalidator<'a, 'b, E>>::invalidate_descendants
  10: <style::invalidation::element::invalidator::TreeStyleInvalidator<'a, 'b, E>>::invalidate
  11: style::data::ElementData::invalidate_style_if_needed
  12: style::traversal::note_children
  13: style::traversal::recalc_style_at
  14: <style::gecko::traversal::RecalcStyleOnly<'recalc> as style::traversal::DomTraversal<style::gecko::wrapper::GeckoElement<'le>>>::process_preorder
  15: style::parallel::traverse_nodes::{{closure}}
  16: rayon_core::scope::Scope::execute_job_closure::{{closure}}
  17: <std::panic::AssertUnwindSafe<F> as core::ops::FnOnce<()>>::call_once
  18: std::panicking::try::do_call
  19: <unknown>
Redirecting call to abort() to mozalloc_abort
"""  # noqa

rustSampleTrace2 = """
thread 'StyleThread#3' panicked at 'assertion failed: self.get_data().is_some()', /home/worker/workspace/build/src/servo/components/style/gecko/wrapper.rs:1040
stack backtrace:
[27247] WARNING: file /home/worker/workspace/build/src/ipc/chromium/src/base/histogram.cc, line 358
   0:     0x7fa1ac1cd783 - std::sys::imp::backtrace::tracing::imp::unwind_backtrace::hcab99e0793da62c7
   1:     0x7fa1ac1c8aa6 - std::sys_common::backtrace::_print::hbfe5b0c7e79c0711
   2:     0x7fa1ac1dae1a - std::panicking::default_hook::{{closure}}::h9ba2c6973907a2be
   3:     0x7fa1ac1daa1b - std::panicking::default_hook::he4d55e2dd21c3cca
   4:     0x7fa1ac1db22b - std::panicking::rust_panic_with_hook::ha138c05cd33ad44d
   5:     0x7fa1abfba7ea - std::panicking::begin_panic::h3893082380049d75
   6:     0x7fa1abe75fe4 - <style::gecko::wrapper::GeckoElement<'le> as style::dom::TElement>::set_dirty_descendants::h7e0109538e4478b9
   7:     0x7fa1ac38d3da - <style::invalidation::element::invalidator::TreeStyleInvalidator<'a, 'b, E>>::invalidate_child::h3f189b4aebe47c62
   8:     0x7fa1ac38dec9 - <style::invalidation::element::invalidator::TreeStyleInvalidator<'a, 'b, E>>::invalidate_dom_descendants_of::h28329f57642c446c
   9:     0x7fa1ac38ddae - <style::invalidation::element::invalidator::TreeStyleInvalidator<'a, 'b, E>>::invalidate_descendants::ha9f8400395e35b97
  10:     0x7fa1ac38d171 - <style::invalidation::element::invalidator::TreeStyleInvalidator<'a, 'b, E>>::invalidate::h55792fb45d7f0193
  11:     0x7fa1ac2cc7fd - style::data::ElementData::invalidate_style_if_needed::h6c92f7a55a3c66c7
  12:     0x7fa1abc3ac26 - style::traversal::note_children::hbf53f5fd19334f04
  13:     0x7fa1ac3453da - style::traversal::recalc_style_at::h2554583039965b7b
  14:     0x7fa1ac31ccfa - <style::gecko::traversal::RecalcStyleOnly<'recalc> as style::traversal::DomTraversal<style::gecko::wrapper::GeckoElement<'le>>>::process_preorder::h5bc6bf3e8a809483
  15:     0x7fa1abc3982c - style::parallel::traverse_nodes::h149467d755f7edde
  16:     0x7fa1abc393c9 - style::parallel::traverse_dom::{{closure}}::{{closure}}::hc41734613847a4b8
  17:     0x7fa1abbee506 - rayon_core::scope::Scope::execute_job_closure::{{closure}}::hb2d2182893d5e162
  18:     0x7fa1abc67852 - <std::panic::AssertUnwindSafe<F> as core::ops::FnOnce<()>>::call_once::h43762f21b8583545
  19:     0x7fa1abc0c962 - std::panicking::try::do_call::h09b210c138cd5782
  20:     0x7fa1ac1dfb0b - <unknown>
Redirecting call to abort() to mozalloc_abort
"""  # noqa

rustSampleTrace3 = """
thread 'StyleThread#2' panicked at 'already mutably borrowed', /home/worker/workspace/build/src/third_party/rust/atomic_refcell/src/lib.rs:161
stack backtrace:
   0:     0x7f6f99931ac3 - std::sys::imp::backtrace::tracing::imp::unwind_backtrace::hcab99e0793da62c7
                               at /checkout/src/libstd/sys/unix/backtrace/tracing/gcc_s.rs:49
   1:     0x7f6f9992ea89 - std::panicking::default_hook::{{closure}}::h9ba2c6973907a2be
                               at /checkout/src/libstd/sys_common/backtrace.rs:71
                               at /checkout/src/libstd/sys_common/backtrace.rs:60
                               at /checkout/src/libstd/panicking.rs:355
   2:     0x7f6f9992deb0 - std::panicking::default_hook::he4d55e2dd21c3cca
                               at /checkout/src/libstd/panicking.rs:371
   3:     0x7f6f9992d9d5 - std::panicking::rust_panic_with_hook::ha138c05cd33ad44d
                               at /checkout/src/libstd/panicking.rs:549
   4:     0x7f6f998b00ef - std::panicking::begin_panic::h4d68aac0b79bfb98
                               at /checkout/src/libstd/panicking.rs:511
   5:     0x7f6f998b00a5 - atomic_refcell::AtomicBorrowRef::do_panic::hbcc7af3a774ab2dd
                               at /home/worker/workspace/build/src/third_party/rust/atomic_refcell/src/lib.rs:161
   6:     0x7f6f99651b83 - <style::values::specified::color::Color as style::values::computed::ToComputedValue>::to_computed_value::h43831540927a6f94
"""  # noqa

rustSampleTrace4 = r"""
thread 'StyleThread#2' panicked at 'already mutably borrowed', Z:\build\build\src\third_party\rust\atomic_refcell\src\lib.rs:161
stack backtrace:
   0:     0x7ffc41f3074f - <unknown>
   1:     0x7ffc41f2f97c - <unknown>
   2:     0x7ffc41f2f1ee - <unknown>
   3:     0x7ffc41f2eacf - <unknown>
OS|Windows NT|10.0.14393
CPU|amd64|family 6 model 94 stepping 3|4
GPU|||
Crash|EXCEPTION_ILLEGAL_INSTRUCTION|0x7ffc41f2f276|36
36|0|xul.dll|std::panicking::rust_panic_with_hook::h4d68aac0b79bfb98|git:github.com/rust-lang/rust:src/libstd/panicking.rs:0ade339411587887bf01bcfa2e9ae4414c8900d4|555|0x41
36|1|xul.dll|std::panicking::begin_panic<&str>::h4d68aac0b79bfb98|git:github.com/rust-lang/rust:src/libstd/panicking.rs:0ade339411587887bf01bcfa2e9ae4414c8900d4|511|0x12
36|2|xul.dll|atomic_refcell::AtomicBorrowRef::do_panic::h4d68aac0b79bfb98|hg:hg.mozilla.org/mozilla-central:third_party/rust/atomic_refcell/src/lib.rs:37b95547f0d2|161|0x18
36|3|xul.dll|style::values::specified::color::{{impl}}::to_computed_value::h4d68aac0b79bfb98|hg:hg.mozilla.org/mozilla-central:servo/components/style/values/specified/color.rs:37b95547f0d2|288|0xc
0|0|ntdll.dll|AslpFilePartialViewFree|||0x36808
0|1|||||0xcd07ffd740
0|2|KERNELBASE.dll|FSPErrorMessages::CMessageHashVectorBuilder::GetEndIndexHash(unsigned short const *)|||0x38
0|3|||||0xcd07ffd740
"""  # noqa

rustSampleTrace5 = """
thread 'RenderBackend' panicked at 'called `Option::unwrap()` on a `None` value', /checkout/src/libcore/option.rs:335:20
stack backtrace:
   0:     0x7f89cd640233 - std::sys::imp::backtrace::tracing::imp::unwind_backtrace::hcdf51e4c9dc54357
                               at /checkout/src/libstd/sys/unix/backtrace/tracing/gcc_s.rs:49
   1:     0x7f89cd63d13f - std::panicking::default_hook::{{closure}}::h46820a72bf0cb624
                               at /checkout/src/libstd/sys_common/backtrace.rs:71
                               at /checkout/src/libstd/sys_common/backtrace.rs:60
                               at /checkout/src/libstd/panicking.rs:380
   2:     0x7f89cd63c58d - std::panicking::default_hook::h4c1ef1cc83189c8e
"""

rustSampleTrace6 = """
thread '<unnamed>' panicked at 'assertion failed: `(left == right)`
  left: `Inline`,
 right: `Block`', /builds/worker/workspace/build/src/servo/components/style/style_adjuster.rs:352:8
stack backtrace:
   0:     0x7f7a3a170663 - std::sys::imp::backtrace::tracing::imp::unwind_backtrace::h8ed7485deb8ab958
   1:     0x7f7a3a16adb0 - std::sys_common::backtrace::_print::h3d4f9ea58578e60f
   2:     0x7f7a3a17db63 - std::panicking::default_hook::{{closure}}::h0088fe51b67c687c
   3:     0x7f7a3a17d8d2 - std::panicking::default_hook::hf425c768c5ffbbad
"""

ubsanTraceGenericCrash = """
==8555==ERROR: UndefinedBehaviorSanitizer: SEGV on unknown address 0x000000004141 (pc 0x7f070b805037 bp 0x7f06626006b0 sp 0x7f0662600680 T28456)
==8555==The signal is caused by a READ memory access.
==8555==Hint: address points to the zero page.
    #0 0x7f070b805036 in mozilla::dom::ToJSValue(JSContext*, mozilla::dom::Promise&, JS::MutableHandle<JS::Value>) (/home/worker/builds/m-c-20200514094044-fuzzing-debug/libxul.so+0x4e3d036)
    #1 0x7f070e4d7a9e in js::jit::DoCallFallback(JSContext*, js::jit::BaselineFrame*, js::jit::ICCall_Fallback*, unsigned int, JS::Value*, JS::MutableHandle<JS::Value>) (/home/worker/builds/m-c-20200514094044-fuzzing-debug/libxul.so+0x7b0fa9e)

UndefinedBehaviorSanitizer can not provide additional info.
==8555==ABORTING
"""  # noqa

ubsanTraceSignedIntOverflow = """
codec/decoder/core/inc/dec_golomb.h:182:37: runtime error: signed integer overflow: -2147483648 - 1 cannot be represented in type 'int'
    #0 0x51353a in WelsDec::BsGetUe(WelsCommon::TagBitStringAux*, unsigned int*) /home/user/code/openh264/./codec/decoder/core/inc/dec_golomb.h:182:37
    #1 0x51a11b in WelsDec::ParseSliceHeaderSyntaxs(WelsDec::TagWelsDecoderContext*, WelsCommon::TagBitStringAux*, bool) /home/user/code/openh264/codec/decoder/core/src/decoder_core.cpp:692:3
    #2 0x59f649 in WelsDec::ParseNalHeader(WelsDec::TagWelsDecoderContext*, WelsCommon::TagNalUnitHeader*, unsigned char*, int, unsigned char*, int, int*) /home/user/code/openh264/codec/decoder/core/src/au_parser.cpp:392:12
    #3 0x50d2fe in WelsDecodeBs /home/user/code/openh264/codec/decoder/core/src/decoder.cpp:749:19
    #4 0x4f3553 in WelsDec::CWelsDecoder::DecodeFrame2(unsigned char const*, int, unsigned char**, TagBufferInfo*) /home/user/code/openh264/codec/decoder/plus/src/welsDecoderExt.cpp:502:3
    #5 0x4f249f in WelsDec::CWelsDecoder::DecodeFrameNoDelay(unsigned char const*, int, unsigned char**, TagBufferInfo*) /home/user/code/openh264/codec/decoder/plus/src/welsDecoderExt.cpp:438:16
    #6 0x4e719f in H264DecodeInstance(ISVCDecoder*, char const*, char const*, int&, int&, char const*, char const*) /home/user/code/openh264/codec/console/dec/src/h264dec.cpp:218:5
    #7 0x4e8630 in main /home/user/code/openh264/codec/console/dec/src/h264dec.cpp:358:5
    #8 0x7fe1d5eb7ec4 in __libc_start_main /build/buildd/eglibc-2.19/csu/libc-start.c:287
    #9 0x41beb5 in _start (/home/user/Desktop/openh264/h264dec_64_ub_asan+0x41beb5)
    #10 0x0 in mozilla::image::nsBMPDecoder::WriteInternal(char const*, unsigned int)::$_0::operator()(mozilla::image::nsBMPDecoder::State, char const*, unsigned long) const /test.cpp:1:1
    #11 0x0 in Lex<<lambda at /builds/slave/m-in-l64-asan-0000000000000000/build/src/image/decoders/nsBMPDecoder.cpp:346:33> > /test.cpp:1:1

SUMMARY: AddressSanitizer: undefined-behavior codec/decoder/core/inc/dec_golomb.h:182:37 in
"""  # noqa

ubsanTraceDivByZero = """
src/opus_demo.c:870:40: runtime error: division by zero
    #0 0x42a550 in main /home/user/code/opus/src/opus_demo.c:870:40
    #1 0x7f751aef582f in __libc_start_main /build/glibc-bfm8X4/glibc-2.23/csu/../csu/libc-start.c:291
    #2 0x402de8 in _start (/home/user/code/opus/opus_demo+0x402de8)
"""

ubsanTraceMissingPattern = """
blah...
blah...
    #0 0x42a550 in main /home/user/code/opus/src/opus_demo.c:870:40
    #1 0x7f751aef582f in __libc_start_main /build/glibc-bfm8X4/glibc-2.23/csu/../csu/libc-start.c:291
    #2 0x402de8 in _start (/home/user/code/opus/opus_demo+0x402de8)
"""

minidumpSwrast = """
OS|Linux|0.0.0 Linux 4.4.0-93-generic #116-Ubuntu SMP Fri Aug 11 21:17:52 UTC 2017 i686
CPU|x86|GenuineIntel family 6 model 63 stepping 2|8
GPU|||
Crash|SIGSEGV|0x40|34
34|0|||||0x9e50a2ee
34|1|swrast_dri.so||||0x470ecc
0|0|linux-gate.so||||0xc31
0|1|libc-2.23.so||||0xf42b2
0|2|libxul.so||||0x43ebda
"""

minidumpMacOS = """
OS|Mac OS X|10.13.6 17G3025
CPU|amd64|family 6 model 23 stepping 10|2
GPU|||
Crash|EXC_BAD_ACCESS / KERN_INVALID_ADDRESS|0x0|0
0|0|XUL|nsIFrame::UpdateOverflow()|hg:hg.mozilla.org/mozilla-central:layout/generic/nsFrame.cpp:957a743c4ca2907d8e357fce43fbcd9f619f1122|7601|0x0
0|1|XUL|mozilla::OverflowChangedTracker::Flush()|hg:hg.mozilla.org/mozilla-central:layout/base/OverflowChangedTracker.h:957a743c4ca2907d8e357fce43fbcd9f619f1122|111|0x8
0|2|XUL|mozilla::RestyleManager::DoProcessPendingRestyles(mozilla::ServoTraversalFlags)|hg:hg.mozilla.org/mozilla-central:layout/base/RestyleManager.h:957a743c4ca2907d8e357fce43fbcd9f619f1122|224|0x5
0|3|XUL|mozilla::PresShell::DoFlushPendingNotifications(mozilla::ChangesToFlush)|hg:hg.mozilla.org/mozilla-central:layout/base/RestyleManager.cpp:957a743c4ca2907d8e357fce43fbcd9f619f1122|3133|0xa
"""  # noqa

lsanTraceLeakDetected = """
=================================================================
==6148==ERROR: LeakSanitizer: detected memory leaks

The 1 top leak(s):
Direct leak of 232 byte(s) in 1 object(s) allocated from:
    #0 0x4c1c93 in malloc /builds/asan_malloc_linux.cc:88:3
    #1 0x4f26fd in moz_xmalloc /builds/mozalloc.cpp:70:17
    #2 0x7fe6cdf7081f in operator new /builds/mozalloc.h:156:12
    #3 0x7fe6cdf7081f in mozilla::net::nsStandardURL::StartClone() /builds/nsStandardURL.cpp:2356
"""


def test_ASanParserTestAccessViolation():
    config = ProgramConfiguration("test", "x86-64", "windows")

    crashInfo = ASanCrashInfo([], asanTraceAV.splitlines(), config)
    assert len(crashInfo.backtrace) == 3
    assert crashInfo.backtrace[0] == "nsCSSFrameConstructor::WipeContainingBlock"
    assert crashInfo.backtrace[1] == "nsCSSFrameConstructor::ContentAppended"
    assert crashInfo.backtrace[2] == "mozilla::RestyleManager::ProcessRestyledFrames"

    assert crashInfo.crashAddress == 0x50
    assert crashInfo.registers["pc"] == 0x7ffa9a30c9e7
    assert crashInfo.registers["sp"] == 0x00f9915f0940
    assert crashInfo.registers["bp"] == 0x00f9915f0a20


def test_ASanParserTestCrash():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = ASanCrashInfo([], asanTraceCrash.splitlines(), config)
    assert len(crashInfo.backtrace) == 7
    assert crashInfo.backtrace[0] == "js::AbstractFramePtr::asRematerializedFrame"
    assert crashInfo.backtrace[2] == "EvalInFrame"
    assert crashInfo.backtrace[3] == "js::CallJSNative"
    assert crashInfo.backtrace[6] == "js::jit::DoCallFallback"

    assert crashInfo.crashAddress == 0x00000014
    assert crashInfo.registers["pc"] == 0x0810845f
    assert crashInfo.registers["sp"] == 0xffc57860
    assert crashInfo.registers["bp"] == 0xffc57f18


def test_ASanParserTestFailedAlloc():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo([], asanTraceFailedAlloc.splitlines(), config)
    assert len(crashInfo.backtrace) == 12
    assert crashInfo.backtrace[0] == "__asan::AsanCheckFailed"
    assert crashInfo.backtrace[7] == "oc_state_frarray_init"

    assert crashInfo.crashAddress is None
    assert not crashInfo.registers

    assert (("AddressSanitizer failed to allocate 0x6003a000 (1610850304) bytes of "
             "LargeMmapAllocator (error code: 12) [@ __asan::AsanCheckFailed]") ==
            crashInfo.createShortSignature())


def test_ASanParserTestAllocSize():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo([], asanTraceAllocSize.splitlines(), config)
    assert len(crashInfo.backtrace) == 1
    assert crashInfo.backtrace[0] == "malloc"

    assert crashInfo.crashAddress is None
    assert not crashInfo.registers

    assert (("AddressSanitizer: requested allocation size exceeds maximum"
             " supported size [@ malloc]") ==
            crashInfo.createShortSignature())


def test_ASanParserTestHeapCrash():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = ASanCrashInfo([], asanTraceHeapCrash.splitlines(), config)
    assert len(crashInfo.backtrace) == 0

    assert crashInfo.crashAddress == 0x00000019
    assert crashInfo.registers["pc"] == 0xf718072e
    assert crashInfo.registers["sp"] == 0xff87d130
    assert crashInfo.registers["bp"] == 0x000006a1

    assert crashInfo.createShortSignature() == "[@ ??]"


def test_ASanParserTestUAF():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo([], asanTraceUAF.splitlines(), config)
    assert len(crashInfo.backtrace) == 23
    assert crashInfo.backtrace[0] == "void mozilla::PodCopy<char16_t>"
    assert crashInfo.backtrace[4] == "JSFunction::native"

    assert crashInfo.crashAddress == 0x7fd766c42800

    assert (("AddressSanitizer: heap-use-after-free [@ void mozilla::PodCopy<char16_t>] "
             "with READ of size 6143520") == crashInfo.createShortSignature())


def test_ASanParserTestInvalidFree():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo([], asanTraceInvalidFree.splitlines(), config)
    assert len(crashInfo.backtrace) == 1
    assert crashInfo.backtrace[0] == "__interceptor_free"

    assert crashInfo.crashAddress == 0x62a00006c200

    assert (("AddressSanitizer: attempting free on address which was not malloc()-ed "
             "[@ __interceptor_free]") == crashInfo.createShortSignature())


def test_ASanParserTestDebugAssertion():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo([], asanTraceDebugAssertion.splitlines(), config)
    assert len(crashInfo.backtrace) == 8
    assert crashInfo.backtrace[0] == "nsCycleCollector::CollectWhite"
    assert crashInfo.backtrace[6] == "mozilla::DefaultDelete<ScopedXPCOMStartup>::operator()"

    assert crashInfo.crashAddress == 0x0

    assert (("Assertion failure: false (An assert from the graphics logger), at "
             "/builds/slave/m-cen-l64-asan-d-0000000000000/build/src/gfx/2d/Logging.h:521") ==
            crashInfo.createShortSignature())


def test_ASanDetectionTest():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo1 = CrashInfo.fromRawCrashData([], [], config, auxCrashData=asanTraceCrash.splitlines())
    crashInfo2 = CrashInfo.fromRawCrashData([], asanTraceUAF.splitlines(), config)

    assert isinstance(crashInfo1, ASanCrashInfo)
    assert isinstance(crashInfo2, ASanCrashInfo)


def test_ASanParserTestParamOverlap():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo([], asanTraceMemcpyParamOverlap.splitlines(), config)
    assert crashInfo.crashAddress is None
    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "__asan_memcpy"
    assert crashInfo.backtrace[1] == "S32_Opaque_BlitRow32"
    assert ("AddressSanitizer: memcpy-param-overlap: memory ranges overlap [@ __asan_memcpy]" ==
            crashInfo.createShortSignature())

    crashInfo = ASanCrashInfo([], asanTraceStrcatParamOverlap.splitlines(), config)
    assert crashInfo.crashAddress is None
    assert len(crashInfo.backtrace) == 1
    assert crashInfo.backtrace[0] == "__interceptor_strcat"
    assert ("AddressSanitizer: strcat-param-overlap: memory ranges overlap [@ __interceptor_strcat]" ==
            crashInfo.createShortSignature())


def test_ASanParserTestMultiTrace():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo([], asanMultiTrace.splitlines(), config)
    assert crashInfo.crashAddress == 0x7f637b59cffc
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "mozilla::ipc::Shmem::OpenExisting"
    assert crashInfo.backtrace[3] == "CreateThread"
    assert "[@ mozilla::ipc::Shmem::OpenExisting]" == crashInfo.createShortSignature()


def test_ASanParserTestTruncatedTrace():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = ASanCrashInfo([], asanTruncatedTrace.splitlines(), config)

    # Make sure we parsed it as a crash, but without a backtrace
    assert len(crashInfo.backtrace) == 0
    assert crashInfo.crashAddress == 0x0

    # Confirm that generating a crash signature will fail
    crashSig = crashInfo.createCrashSignature()
    assert crashSig is None
    assert "Insufficient data" in crashInfo.failureReason


def test_GDBParserTestCrash():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo = GDBCrashInfo([], gdbSampleTrace1.splitlines(), config)
    assert len(crashInfo.backtrace) == 8
    assert crashInfo.backtrace[0] == "internalAppend<js::ion::MDefinition*>"
    assert crashInfo.backtrace[2] == "js::ion::MPhi::addInput"
    assert crashInfo.backtrace[6] == "processCfgStack"

    assert crashInfo.registers["eax"] == 0x0
    assert crashInfo.registers["ebx"] == 0x8962ff4
    assert crashInfo.registers["eip"] == 0x818bc33


def test_GDBParserTestCrashAddress():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo1 = GDBCrashInfo([], gdbCrashAddress1.splitlines(), config)
    crashInfo2 = GDBCrashInfo([], gdbCrashAddress2.splitlines(), config)
    crashInfo3 = GDBCrashInfo([], gdbCrashAddress3.splitlines(), config)
    crashInfo4 = GDBCrashInfo([], gdbCrashAddress4.splitlines(), config)
    crashInfo5 = GDBCrashInfo([], gdbCrashAddress5.splitlines(), config)

    assert crashInfo1.crashAddress == 0x1
    assert crashInfo2.crashAddress == 0x0
    assert crashInfo3.crashAddress == 0xffffffffffffffa0
    assert crashInfo4.crashAddress == 0x3ef29d14
    assert crashInfo5.crashAddress == 0x87afa014


def test_GDBParserTestCrashAddressSimple():
    registerMap64 = {}
    registerMap64["rax"] = 0x0
    registerMap64["rbx"] = -1
    registerMap64["rsi"] = 0xde6e5
    registerMap64["rdi"] = 0x7ffff6543238

    registerMap32 = {}
    registerMap32["eax"] = 0x0
    registerMap32["ebx"] = -1
    registerMap32["ecx"] = 0xf75fffb8

    # Simple tests
    assert GDBCrashInfo.calculateCrashAddress("mov    %rbx,0x10(%rax)", registerMap64) == 0x10
    assert GDBCrashInfo.calculateCrashAddress("mov    %ebx,0x10(%eax)", registerMap32) == 0x10

    # Overflow tests
    assert GDBCrashInfo.calculateCrashAddress("mov    %rax,0x10(%rbx)", registerMap64) == 0xF
    assert GDBCrashInfo.calculateCrashAddress("mov    %eax,0x10(%ebx)", registerMap32) == 0xF

    assert GDBCrashInfo.calculateCrashAddress("mov    %rbx,-0x10(%rax)", registerMap64) == -16
    assert GDBCrashInfo.calculateCrashAddress("mov    %ebx,-0x10(%eax)", registerMap32) == -16

    # Scalar test
    assert GDBCrashInfo.calculateCrashAddress("movl   $0x7b,0x0", registerMap32) == 0x0

    # Real world examples
    # Note: The crash address here can also be 0xf7600000 because the double quadword
    # move can fail on the second 8 bytes if the source address is not 16-byte aligned
    assert (GDBCrashInfo.calculateCrashAddress("movdqu 0x40(%ecx),%xmm4", registerMap32) ==
            int32(0xf75ffff8))

    # Again, this is an unaligned access and the crash can be at 0x7ffff6700000 or 0x7ffff6700000 - 4
    assert (GDBCrashInfo.calculateCrashAddress("mov    -0x4(%rdi,%rsi,2),%eax", registerMap64) ==
            0x7ffff66ffffe)


def test_GDBParserTestRegression1():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo1 = GDBCrashInfo([], gdbRegressionTrace1.splitlines(), config)

    assert crashInfo1.backtrace[0] == "js::ScriptedIndirectProxyHandler::defineProperty"
    assert crashInfo1.backtrace[1] == "js::SetPropertyIgnoringNamedGetter"


def test_GDBParserTestCrashAddressRegression2():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo2 = GDBCrashInfo([], gdbRegressionTrace2.splitlines(), config)

    assert crashInfo2.crashAddress == 0xfffd579c


def test_GDBParserTestCrashAddressRegression3():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo3 = GDBCrashInfo([], gdbRegressionTrace3.splitlines(), config)

    assert crashInfo3.crashAddress == 0x7fffffffffff


def test_GDBParserTestCrashAddressRegression4():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo4 = GDBCrashInfo([], gdbRegressionTrace4.splitlines(), config)

    assert crashInfo4.crashAddress == 0x0


def test_GDBParserTestCrashAddressRegression5():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo5 = GDBCrashInfo([], gdbRegressionTrace5.splitlines(), config)

    assert crashInfo5.crashAddress == 0xfffd573c


def test_GDBParserTestCrashAddressRegression6():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo6 = GDBCrashInfo([], gdbRegressionTrace6.splitlines(), config)

    assert crashInfo6.crashAddress == 0xf7673132


def test_GDBParserTestCrashAddressRegression7():
    config = ProgramConfiguration("test", "x86", "linux")

    # This used to fail because CrashInfo.fromRawCrashData fails to detect a GDB trace
    crashInfo7 = CrashInfo.fromRawCrashData([], [], config, gdbRegressionTrace7.splitlines())

    assert crashInfo7.backtrace[1] == "js::ScopeIter::settle"


def test_GDBParserTestCrashAddressRegression8():
    config = ProgramConfiguration("test", "x86", "linux")

    # This used to fail because CrashInfo.fromRawCrashData fails to detect a GDB trace
    crashInfo8 = CrashInfo.fromRawCrashData([], [], config, gdbRegressionTrace8.splitlines())

    assert crashInfo8.backtrace[2] == "js::jit::AutoLockSimulatorCache::AutoLockSimulatorCache"
    assert crashInfo8.backtrace[3] == "<signal handler called>"
    assert crashInfo8.backtrace[4] == "??"
    assert crashInfo8.backtrace[5] == "js::jit::CheckICacheLocked"


def test_GDBParserTestCrashAddressRegression9():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo9 = CrashInfo.fromRawCrashData([], [], config, gdbRegressionTrace9.splitlines())
    assert crashInfo9.crashInstruction == "call   0x8120ca0"


def test_GDBParserTestCrashAddressRegression10():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo10 = CrashInfo.fromRawCrashData([], [], config, gdbRegressionTrace10.splitlines())
    assert crashInfo10.crashInstruction == "(bad)"
    assert crashInfo10.crashAddress == 0x7ff7f20c1f81


def test_GDBParserTestCrashAddressRegression11():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo11 = CrashInfo.fromRawCrashData([], [], config, gdbRegressionTrace11.splitlines())
    assert crashInfo11.crashInstruction == "callq  *0xa8(%rax)"
    assert crashInfo11.crashAddress == 0x7ff7f2091032


def test_GDBParserTestCrashAddressRegression12():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo12 = CrashInfo.fromRawCrashData([], [], config, gdbRegressionTrace12.splitlines())
    assert crashInfo12.backtrace[0] == "js::SavedStacks::insertFrames"
    assert crashInfo12.backtrace[1] == "js::SavedStacks::saveCurrentStack"
    assert crashInfo12.backtrace[2] == "JS::CaptureCurrentStack"
    assert crashInfo12.backtrace[3] == "CaptureStack"


def test_GDBParserTestCrashAddressRegression13():
    config = ProgramConfiguration("test", "x86", "linux")

    crashInfo13 = CrashInfo.fromRawCrashData([], [], config, gdbRegressionTrace13.splitlines())
    assert crashInfo13.backtrace[0] == "JSScript::global"
    assert crashInfo13.backtrace[1] == "js::AbstractFramePtr::global"
    assert crashInfo13.backtrace[5] == "js::jit::HandleException"
    assert crashInfo13.backtrace[6] == "??"

    assert crashInfo13.crashInstruction == "pushl  0x10(%eax)"
    assert crashInfo13.crashAddress == 0xe5e5e5f5


def test_CrashSignatureOutputTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashSignature1 = '{ "symptoms" : [ { "type" : "output", "value" : "test" } ] }'
    crashSignature1Neg = '{ "symptoms" : [ { "type" : "output", "src" : "stderr", "value" : "test" } ] }'
    crashSignature2 = ('{ "symptoms" : [ { "type" : "output", "src" : "stderr", "value" : { '
                       '"value" : "^fest$", "matchType" : "pcre" } } ] }')

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

    crashInfo = CrashInfo.fromRawCrashData(stdout, stderr, config, auxCrashData=gdbOutput)

    assert isinstance(crashInfo, NoCrashInfo)

    # Ensure we match on stdout/err if nothing is specified
    assert outputSignature1.matches(crashInfo)

    # Don't match stdout if stderr is specified
    assert not outputSignature1Neg.matches(crashInfo)

    # Check that we're really using PCRE
    assert not outputSignature2.matches(crashInfo)

    # Add something the PCRE should match, then retry
    stderr.append("fest")
    crashInfo = CrashInfo.fromRawCrashData(stdout, stderr, config, auxCrashData=gdbOutput)
    assert outputSignature2.matches(crashInfo)


def test_CrashSignatureAddressTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashSignature1 = '{ "symptoms" : [ { "type" : "crashAddress", "address" : "< 0x1000" } ] }'
    crashSignature1Neg = '{ "symptoms" : [ { "type" : "crashAddress", "address" : "0x1000" } ] }'
    addressSig1 = CrashSignature(crashSignature1)
    addressSig1Neg = CrashSignature(crashSignature1Neg)

    crashInfo1 = CrashInfo.fromRawCrashData([], [], config, auxCrashData=gdbSampleTrace1.splitlines())
    crashInfo3 = CrashInfo.fromRawCrashData([], [], config, auxCrashData=gdbSampleTrace3.splitlines())

    assert isinstance(crashInfo1, GDBCrashInfo)

    assert addressSig1.matches(crashInfo1)
    assert not addressSig1Neg.matches(crashInfo1)

    # For crashInfo3, we don't have a crash address. Ensure we don't match
    assert not addressSig1.matches(crashInfo3)
    assert not addressSig1Neg.matches(crashInfo3)


def test_CrashSignatureRegisterTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashSignature1 = '{ "symptoms" : [ { "type" : "instruction", "registerNames" : ["r14"] } ] }'
    crashSignature1Neg = '{ "symptoms" : [ { "type" : "instruction", "registerNames" : ["r14", "rax"] } ] }'
    crashSignature2 = '{ "symptoms" : [ { "type" : "instruction", "instructionName" : "mov" } ] }'
    crashSignature2Neg = '{ "symptoms" : [ { "type" : "instruction", "instructionName" : "cmp" } ] }'
    crashSignature3 = ('{ "symptoms" : [ { "type" : "instruction", "instructionName" : "mov", '
                       '"registerNames" : ["r14", "rbx"] } ] }')
    crashSignature3Neg = ('{ "symptoms" : [ { "type" : "instruction", "instructionName" : "mov", '
                          '"registerNames" : ["r14", "rax"] } ] }')

    instructionSig1 = CrashSignature(crashSignature1)
    instructionSig1Neg = CrashSignature(crashSignature1Neg)

    instructionSig2 = CrashSignature(crashSignature2)
    instructionSig2Neg = CrashSignature(crashSignature2Neg)

    instructionSig3 = CrashSignature(crashSignature3)
    instructionSig3Neg = CrashSignature(crashSignature3Neg)

    crashInfo2 = CrashInfo.fromRawCrashData([], [], config, auxCrashData=gdbSampleTrace2.splitlines())
    crashInfo3 = CrashInfo.fromRawCrashData([], [], config, auxCrashData=gdbSampleTrace3.splitlines())

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

    crashSignature1 = '{ "symptoms" : [ { "type" : "stackFrame", "functionName" : "internalAppend" } ] }'
    crashSignature1Neg = '{ "symptoms" : [ { "type" : "stackFrame", "functionName" : "foobar" } ] }'

    crashSignature2 = ('{ "symptoms" : [ { "type" : "stackFrame", '
                       '"functionName" : "js::ion::MBasicBlock::setBackedge", "frameNumber" : "<= 4" } ] }')
    crashSignature2Neg = ('{ "symptoms" : [ { "type" : "stackFrame", '
                          '"functionName" : "js::ion::MBasicBlock::setBackedge", "frameNumber" : "> 4" } ] }')

    stackFrameSig1 = CrashSignature(crashSignature1)
    stackFrameSig1Neg = CrashSignature(crashSignature1Neg)

    stackFrameSig2 = CrashSignature(crashSignature2)
    stackFrameSig2Neg = CrashSignature(crashSignature2Neg)

    crashInfo1 = CrashInfo.fromRawCrashData([], [], config, auxCrashData=gdbSampleTrace1.splitlines())

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
    crashSignature2Neg = '{ "symptoms" : [ { "type" : "stackSize", "size" : "> 10" } ] }'

    stackSizeSig1 = CrashSignature(crashSignature1)
    stackSizeSig1Neg = CrashSignature(crashSignature1Neg)

    stackSizeSig2 = CrashSignature(crashSignature2)
    stackSizeSig2Neg = CrashSignature(crashSignature2Neg)

    crashInfo1 = CrashInfo.fromRawCrashData([], [], config, auxCrashData=gdbSampleTrace1.splitlines())

    assert isinstance(crashInfo1, GDBCrashInfo)

    assert stackSizeSig1.matches(crashInfo1)
    assert not stackSizeSig1Neg.matches(crashInfo1)

    assert stackSizeSig2.matches(crashInfo1)
    assert not stackSizeSig2Neg.matches(crashInfo1)


def test_RegisterHelperValueTest():
    registerMap = {"rax": 0xfffffffffffffe00, "rbx": 0x7ffff79a7640}

    assert RegisterHelper.getRegisterValue("rax", registerMap) == 0xfffffffffffffe00
    assert RegisterHelper.getRegisterValue("eax", registerMap) == 0xfffffe00
    assert RegisterHelper.getRegisterValue("ax", registerMap) == 0xfe00
    assert RegisterHelper.getRegisterValue("ah", registerMap) == 0xfe
    assert RegisterHelper.getRegisterValue("al", registerMap) == 0x0

    assert RegisterHelper.getRegisterValue("rbx", registerMap) == 0x7ffff79a7640
    assert RegisterHelper.getRegisterValue("ebx", registerMap) == 0xf79a7640
    assert RegisterHelper.getRegisterValue("bx", registerMap) == 0x7640
    assert RegisterHelper.getRegisterValue("bh", registerMap) == 0x76
    assert RegisterHelper.getRegisterValue("bl", registerMap) == 0x40


def test_MinidumpParserTestCrash():
    config = ProgramConfiguration("test", "x86", "linux")

    with open(os.path.join(CWD, 'resources', 'minidump-example.txt'), 'r') as f:
        crashInfo = MinidumpCrashInfo([], f.read().splitlines(), config)

    assert len(crashInfo.backtrace) == 44
    assert crashInfo.backtrace[0] == "libc-2.15.so+0xe6b03"
    assert crashInfo.backtrace[5] == "libglib-2.0.so.0.3200.1+0x48123"
    assert crashInfo.backtrace[6] == "nsAppShell::ProcessNextNativeEvent"
    assert crashInfo.backtrace[7] == "nsBaseAppShell::DoProcessNextNativeEvent"

    assert crashInfo.crashAddress == 0x3e800006acb


def test_MinidumpSelectorTest():
    config = ProgramConfiguration("test", "x86", "linux")

    with open(os.path.join(CWD, 'resources', 'minidump-example.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x3e800006acb


def test_MinidumpFromMacOSTest():
    config = ProgramConfiguration("test", "x86-64", "macosx")

    crashInfo = CrashInfo.fromRawCrashData([], [], config, minidumpMacOS.splitlines())
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "nsIFrame::UpdateOverflow"
    assert crashInfo.backtrace[1] == "mozilla::OverflowChangedTracker::Flush"
    assert crashInfo.backtrace[2] == "mozilla::RestyleManager::DoProcessPendingRestyles"
    assert crashInfo.backtrace[3] == "mozilla::PresShell::DoFlushPendingNotifications"
    assert crashInfo.crashAddress == 0


def test_AppleParserTestCrash():
    config = ProgramConfiguration("test", "x86-64", "macosx")

    with open(os.path.join(CWD, 'resources', 'apple-crash-report-example.txt'), 'r') as f:
        crashInfo = AppleCrashInfo([], [], config, f.read().splitlines())

    assert len(crashInfo.backtrace) == 9
    assert crashInfo.backtrace[0] == "js::jit::MacroAssembler::Pop"
    assert crashInfo.backtrace[1] == "js::jit::ICGetPropCallNativeCompiler::generateStubCode"
    assert crashInfo.backtrace[2] == "js::jit::ICStubCompiler::getStubCode"
    assert crashInfo.backtrace[3] == "js::jit::ICGetPropCallNativeCompiler::getStub"
    assert crashInfo.backtrace[4] == "js::jit::DoGetPropFallback"
    assert crashInfo.backtrace[5] == "??"
    assert crashInfo.backtrace[6] == "__cxa_finalize_ranges"
    assert crashInfo.backtrace[7] == "??"
    assert (crashInfo.backtrace[8] == "-[NSApplication _nextEventMatchingEventMask:untilDate:inMode:dequeue:]")

    assert crashInfo.crashAddress == 0x00007fff5f3fff98


def test_AppleSelectorTest():
    config = ProgramConfiguration("test", "x86-64", "macosx")

    with open(os.path.join(CWD, 'resources', 'apple-crash-report-example.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00007fff5f3fff98


def test_AppleLionParserTestCrash():
    config = ProgramConfiguration("test", "x86-64", "macosx64")

    with open(os.path.join(CWD, 'resources', 'apple-10-7-crash-report-example.txt'), 'r') as f:
        crashInfo = AppleCrashInfo([], [], config, f.read().splitlines())

    assert len(crashInfo.backtrace) == 13
    assert crashInfo.backtrace[0] == "js::jit::LIRGenerator::visitNearbyInt"
    assert crashInfo.backtrace[1] == "js::jit::LIRGenerator::visitInstruction"
    assert crashInfo.backtrace[2] == "js::jit::LIRGenerator::visitBlock"
    assert crashInfo.backtrace[3] == "js::jit::LIRGenerator::generate"
    assert crashInfo.backtrace[4] == "js::jit::GenerateLIR"
    assert crashInfo.backtrace[5] == "js::jit::CompileBackEnd"
    assert (crashInfo.backtrace[6] == ("_ZN2js3jitL7CompileEP9JSContextN2JS6Handle"
                                       "IP8JSScriptEEPNS0_13BaselineFrameEPhb"))
    assert crashInfo.backtrace[7] == "js::jit::IonCompileScriptForBaseline"
    assert crashInfo.backtrace[8] == "??"
    assert crashInfo.backtrace[9] == "??"
    assert crashInfo.backtrace[10] == "??"
    assert crashInfo.backtrace[11] == "??"
    assert crashInfo.backtrace[12] == "_ZL13EnterBaselineP9JSContextRN2js3jit12EnterJitDataE"

    assert crashInfo.crashAddress == 0x0000000000000000


def test_AppleLionSelectorTest():
    config = ProgramConfiguration("test", "x86-64", "macosx64")

    with open(os.path.join(CWD, 'resources', 'apple-10-7-crash-report-example.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x0000000000000000


# Test 1a is for Win7 with 32-bit js debug deterministic shell hitting the assertion failure:
#     js_dbg_32_dm_windows_62f79d676e0e!js::GetBytecodeLength
#     01814577 cc              int     3
def test_CDBParserTestCrash1a():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-1a-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

    assert len(crashInfo.backtrace) == 13
    assert crashInfo.backtrace[0] == "js::GetBytecodeLength"
    assert crashInfo.backtrace[1] == "js::coverage::LCovSource::writeScript"
    assert crashInfo.backtrace[2] == "js::coverage::LCovCompartment::collectCodeCoverageInfo"
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
    assert crashInfo.registers["ecx"] == 0x6a24705d
    assert crashInfo.registers["edx"] == 0x0034d9d4
    assert crashInfo.registers["esi"] == 0x0925b3ec
    assert crashInfo.registers["edi"] == 0x0925b3d1
    assert crashInfo.registers["eip"] == 0x01814577
    assert crashInfo.registers["esp"] == 0x0034ef5c
    assert crashInfo.registers["ebp"] == 0x0034ef5c

    assert crashInfo.crashAddress == 0x01814577


def test_CDBSelectorTest1a():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-1a-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x01814577


# Test 1b is for Win10 with 32-bit js debug deterministic shell hitting the assertion failure:
#     js_dbg_32_dm_windows_62f79d676e0e!js::GetBytecodeLength+47
#     01344577 cc              int     3
def test_CDBParserTestCrash1b():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-1b-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

    assert len(crashInfo.backtrace) == 13
    assert crashInfo.backtrace[0] == "js::GetBytecodeLength"
    assert crashInfo.backtrace[1] == "js::coverage::LCovSource::writeScript"
    assert crashInfo.backtrace[2] == "js::coverage::LCovCompartment::collectCodeCoverageInfo"
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
    assert crashInfo.registers["ecx"] == 0x765e06ef
    assert crashInfo.registers["edx"] == 0x00000060
    assert crashInfo.registers["esi"] == 0x039604ec
    assert crashInfo.registers["edi"] == 0x039604d1
    assert crashInfo.registers["eip"] == 0x01344577
    assert crashInfo.registers["esp"] == 0x02b2ee1c
    assert crashInfo.registers["ebp"] == 0x02b2ee1c

    assert crashInfo.crashAddress == 0x01344577


def test_CDBSelectorTest1b():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-1b-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x01344577


# Test 2a is for Win7 with 64-bit js debug deterministic shell hitting the assertion failure:
#     js_dbg_64_dm_windows_62f79d676e0e!js::GetBytecodeLength
#     00000001`40144e62 cc              int     3
def test_CDBParserTestCrash2a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-2a-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

    assert len(crashInfo.backtrace) == 25
    assert crashInfo.backtrace[0] == "js::GetBytecodeLength"
    assert crashInfo.backtrace[1] == "js::coverage::LCovSource::writeScript"
    assert crashInfo.backtrace[2] == "js::coverage::LCovCompartment::collectCodeCoverageInfo"
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
    assert crashInfo.registers["rbx"] == 0x0000000006c139ac
    assert crashInfo.registers["rcx"] == 0x000007fef38241f0
    assert crashInfo.registers["rdx"] == 0x000007fef38255f0
    assert crashInfo.registers["rsi"] == 0x0000000006c1399e
    assert crashInfo.registers["rdi"] == 0x0000000006cf2101
    assert crashInfo.registers["rip"] == 0x0000000140144e62
    assert crashInfo.registers["rsp"] == 0x000000000027e500
    assert crashInfo.registers["rbp"] == 0x0000000006cf2120
    assert crashInfo.registers["r8"] == 0x000000000027ce88
    assert crashInfo.registers["r9"] == 0x00000000020cc069
    assert crashInfo.registers["r10"] == 0x0000000000000000
    assert crashInfo.registers["r11"] == 0x000000000027e3f0
    assert crashInfo.registers["r12"] == 0x0000000006c0d088
    assert crashInfo.registers["r13"] == 0x0000000006c139ad
    assert crashInfo.registers["r14"] == 0x0000000000000000
    assert crashInfo.registers["r15"] == 0x0000000006c13991

    assert crashInfo.crashAddress == 0x0000000140144e62


def test_CDBSelectorTest2a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-2a-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x0000000140144e62


# Test 2b is for Win10 with 64-bit js debug deterministic shell hitting the assertion failure:
#     js_dbg_64_dm_windows_62f79d676e0e!js::GetBytecodeLength+52
#     00007ff7`1e424e62 cc              int     3
def test_CDBParserTestCrash2b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-2b-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

    assert len(crashInfo.backtrace) == 25
    assert crashInfo.backtrace[0] == "js::GetBytecodeLength"
    assert crashInfo.backtrace[1] == "js::coverage::LCovSource::writeScript"
    assert crashInfo.backtrace[2] == "js::coverage::LCovCompartment::collectCodeCoverageInfo"
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
    assert crashInfo.registers["rbx"] == 0x0000024dbf40baac
    assert crashInfo.registers["rcx"] == 0x00000000ffffffff
    assert crashInfo.registers["rdx"] == 0x0000000000000000
    assert crashInfo.registers["rsi"] == 0x0000024dbf40ba9e
    assert crashInfo.registers["rdi"] == 0x0000024dbf4f2201
    assert crashInfo.registers["rip"] == 0x00007ff71e424e62
    assert crashInfo.registers["rsp"] == 0x000000de223fe3d0
    assert crashInfo.registers["rbp"] == 0x0000024dbf4f22e0
    assert crashInfo.registers["r8"] == 0x000000de223fcd78
    assert crashInfo.registers["r9"] == 0x0000024dbebe0735
    assert crashInfo.registers["r10"] == 0x0000000000000000
    assert crashInfo.registers["r11"] == 0x000000de223fe240
    assert crashInfo.registers["r12"] == 0x0000024dbf414088
    assert crashInfo.registers["r13"] == 0x0000024dbf40baad
    assert crashInfo.registers["r14"] == 0x0000000000000000
    assert crashInfo.registers["r15"] == 0x0000024dbf40ba91

    assert crashInfo.crashAddress == 0x00007ff71e424e62


def test_CDBSelectorTest2b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-2b-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00007ff71e424e62


# Test 3a is for Win7 with 32-bit js debug deterministic shell crashing:
#     js_dbg_32_dm_windows_62f79d676e0e!js::gc::TenuredCell::arena
#     00f36a63 8b00            mov     eax,dword ptr [eax]
def test_CDBParserTestCrash3a():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-3a-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

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
    assert crashInfo.registers["eax"] == 0x2b2ffff0
    assert crashInfo.registers["ebx"] == 0x0041de08
    assert crashInfo.registers["ecx"] == 0x2b2b2b2b
    assert crashInfo.registers["edx"] == 0x0a200310
    assert crashInfo.registers["esi"] == 0x0041dc68
    assert crashInfo.registers["edi"] == 0x0a200310
    assert crashInfo.registers["eip"] == 0x00f36a63
    assert crashInfo.registers["esp"] == 0x0041dc04
    assert crashInfo.registers["ebp"] == 0x0041dc2c

    assert crashInfo.crashAddress == 0x00f36a63


def test_CDBSelectorTest3a():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-3a-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00f36a63


# Test 3b is for Win10 with 32-bit js debug deterministic shell crashing:
#     js_dbg_32_dm_windows_62f79d676e0e!js::gc::TenuredCell::arena+13
#     00ed6a63 8b00            mov     eax,dword ptr [eax]
def test_CDBParserTestCrash3b():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-3b-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

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
    assert crashInfo.registers["eax"] == 0x2b2ffff0
    assert crashInfo.registers["ebx"] == 0x02b2deb8
    assert crashInfo.registers["ecx"] == 0x2b2b2b2b
    assert crashInfo.registers["edx"] == 0x04200310
    assert crashInfo.registers["esi"] == 0x02b2dd18
    assert crashInfo.registers["edi"] == 0x04200310
    assert crashInfo.registers["eip"] == 0x00ed6a63
    assert crashInfo.registers["esp"] == 0x02b2dcb4
    assert crashInfo.registers["ebp"] == 0x02b2dcdc

    assert crashInfo.crashAddress == 0x00ed6a63


def test_CDBSelectorTest3b():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-3b-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00ed6a63


# Test 4a is for Win7 with 32-bit js opt deterministic shell crashing:
#     js_32_dm_windows_62f79d676e0e!JSObject::allocKindForTenure
#     00d44c59 8b39            mov     edi,dword ptr [ecx]
def test_CDBParserTestCrash4a():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-4a-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

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
    assert crashInfo.registers["eax"] == 0x09bfff01
    assert crashInfo.registers["ebx"] == 0x002adc18
    assert crashInfo.registers["ecx"] == 0x2b2b2b2b
    assert crashInfo.registers["edx"] == 0x002ae2f0
    assert crashInfo.registers["esi"] == 0x09b00310
    assert crashInfo.registers["edi"] == 0x09b00310
    assert crashInfo.registers["eip"] == 0x00d44c59
    assert crashInfo.registers["esp"] == 0x002ada8c
    assert crashInfo.registers["ebp"] == 0x002adc18

    assert crashInfo.crashAddress == 0x00d44c59


def test_CDBSelectorTest4a():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-4a-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00d44c59


# Test 4b is for Win10 with 32-bit js opt deterministic shell crashing:
#     js_32_dm_windows_62f79d676e0e!JSObject::allocKindForTenure+9
#     00404c59 8b39            mov     edi,dword ptr [ecx]
def test_CDBParserTestCrash4b():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-4b-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

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
    assert crashInfo.registers["eax"] == 0x02efff01
    assert crashInfo.registers["ebx"] == 0x016fddb8
    assert crashInfo.registers["ecx"] == 0x2b2b2b2b
    assert crashInfo.registers["edx"] == 0x016fe490
    assert crashInfo.registers["esi"] == 0x02e00310
    assert crashInfo.registers["edi"] == 0x02e00310
    assert crashInfo.registers["eip"] == 0x00404c59
    assert crashInfo.registers["esp"] == 0x016fdc2c
    assert crashInfo.registers["ebp"] == 0x016fddb8

    assert crashInfo.crashAddress == 0x00404c59


def test_CDBSelectorTest4b():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-4b-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00404c59


# Test 5a is for Win7 with 64-bit js debug deterministic shell crashing:
#     js_dbg_64_dm_windows_62f79d676e0e!js::gc::IsInsideNursery
#     00000001`3f4975db 8b11            mov     edx,dword ptr [rcx]
def test_CDBParserTestCrash5a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-5a-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

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
    assert crashInfo.registers["rbx"] == 0xfffe2b2b2b2b2b2b
    assert crashInfo.registers["rcx"] == 0xfffe2b2b2b2fffe8
    assert crashInfo.registers["rdx"] == 0x0000000000000001
    assert crashInfo.registers["rsi"] == 0x000000000040c078
    assert crashInfo.registers["rdi"] == 0x0000000006a00420
    assert crashInfo.registers["rip"] == 0x000000013f4975db
    assert crashInfo.registers["rsp"] == 0x000000000040bc40
    assert crashInfo.registers["rbp"] == 0x0000000000000006
    assert crashInfo.registers["r8"] == 0x0000000006633200
    assert crashInfo.registers["r9"] == 0x000000014079b1a0
    assert crashInfo.registers["r10"] == 0x0000000000000031
    assert crashInfo.registers["r11"] == 0x0000000000000033
    assert crashInfo.registers["r12"] == 0xfffa7fffffffffff
    assert crashInfo.registers["r13"] == 0xfffc000000000000
    assert crashInfo.registers["r14"] == 0x000000000040c078
    assert crashInfo.registers["r15"] == 0x000000014079b1a0

    assert crashInfo.crashAddress == 0x000000013f4975db


def test_CDBSelectorTest5a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-5a-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x000000013f4975db


# Test 5b is for Win10 with 64-bit js debug deterministic shell crashing:
#     js_dbg_64_dm_windows_62f79d676e0e!js::gc::IsInsideNursery+1b
#     00007ff7`1dcf75db 8b11            mov     edx,dword ptr [rcx]
def test_CDBParserTestCrash5b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-5b-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

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
    assert crashInfo.registers["rbx"] == 0xfffe2b2b2b2b2b2b
    assert crashInfo.registers["rcx"] == 0xfffe2b2b2b2fffe8
    assert crashInfo.registers["rdx"] == 0x0000000000000001
    assert crashInfo.registers["rsi"] == 0x000000c4a47fc528
    assert crashInfo.registers["rdi"] == 0x0000021699700420
    assert crashInfo.registers["rip"] == 0x00007ff71dcf75db
    assert crashInfo.registers["rsp"] == 0x000000c4a47fc0f0
    assert crashInfo.registers["rbp"] == 0x0000000000000006
    assert crashInfo.registers["r8"] == 0x0000021699633200
    assert crashInfo.registers["r9"] == 0x00007ff71effa590
    assert crashInfo.registers["r10"] == 0x0000000000000031
    assert crashInfo.registers["r11"] == 0x0000000000000033
    assert crashInfo.registers["r12"] == 0xfffa7fffffffffff
    assert crashInfo.registers["r13"] == 0xfffc000000000000
    assert crashInfo.registers["r14"] == 0x000000c4a47fc528
    assert crashInfo.registers["r15"] == 0x00007ff71effa590

    assert crashInfo.crashAddress == 0x00007ff71dcf75db


def test_CDBSelectorTest5b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-5b-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00007ff71dcf75db


# Test 6a is for Win7 with 64-bit js opt deterministic shell crashing:
#     js_64_dm_windows_62f79d676e0e!JSObject::allocKindForTenure
#     00000001`3f869ff3 4c8b01          mov     r8,qword ptr [rcx]
def test_CDBParserTestCrash6a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-6a-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

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
    assert crashInfo.registers["rax"] == 0x000000013fcfeef0
    assert crashInfo.registers["rbx"] == 0x0000000008d00420
    assert crashInfo.registers["rcx"] == 0x2b2b2b2b2b2b2b2b
    assert crashInfo.registers["rdx"] == 0x000000000681b940
    assert crashInfo.registers["rsi"] == 0x000000000034c7b0
    assert crashInfo.registers["rdi"] == 0x0000000008d00420
    assert crashInfo.registers["rip"] == 0x000000013f869ff3
    assert crashInfo.registers["rsp"] == 0x000000000034c4b0
    assert crashInfo.registers["rbp"] == 0xfffe000000000000
    assert crashInfo.registers["r8"] == 0x000000000034c5b0
    assert crashInfo.registers["r9"] == 0x000000000001fffc
    assert crashInfo.registers["r10"] == 0x000000000000061d
    assert crashInfo.registers["r11"] == 0x000000000685a000
    assert crashInfo.registers["r12"] == 0x000000013fd23a98
    assert crashInfo.registers["r13"] == 0xfffa7fffffffffff
    assert crashInfo.registers["r14"] == 0x000000000034d550
    assert crashInfo.registers["r15"] == 0x0000000000000003

    assert crashInfo.crashAddress == 0x000000013f869ff3


def test_CDBSelectorTest6a():
    config = ProgramConfiguration("test", "x86-64", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-6a-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x000000013f869ff3


# Test 6b is for Win10 with 64-bit js opt deterministic shell crashing:
#     js_64_dm_windows_62f79d676e0e!JSObject::allocKindForTenure+13
#     00007ff7`4d469ff3 4c8b01          mov     r8,qword ptr [rcx]
def test_CDBParserTestCrash6b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-6b-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

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
    assert crashInfo.registers["rax"] == 0x00007ff74d8fee30
    assert crashInfo.registers["rbx"] == 0x00000285ef400420
    assert crashInfo.registers["rcx"] == 0x2b2b2b2b2b2b2b2b
    assert crashInfo.registers["rdx"] == 0x00000285ef21b940
    assert crashInfo.registers["rsi"] == 0x000000e87fbfc340
    assert crashInfo.registers["rdi"] == 0x00000285ef400420
    assert crashInfo.registers["rip"] == 0x00007ff74d469ff3
    assert crashInfo.registers["rsp"] == 0x000000e87fbfc040
    assert crashInfo.registers["rbp"] == 0xfffe000000000000
    assert crashInfo.registers["r8"] == 0x00000e87fbfc140
    assert crashInfo.registers["r9"] == 0x00000000001fffc
    assert crashInfo.registers["r10"] == 0x0000000000000649
    assert crashInfo.registers["r11"] == 0x00000285ef25a000
    assert crashInfo.registers["r12"] == 0x00007ff74d9239a0
    assert crashInfo.registers["r13"] == 0xfffa7fffffffffff
    assert crashInfo.registers["r14"] == 0x000000e87fbfd0e0
    assert crashInfo.registers["r15"] == 0x0000000000000003

    assert crashInfo.crashAddress == 0x00007ff74d469ff3


def test_CDBSelectorTest6b():
    config = ProgramConfiguration("test", "x86-64", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-6b-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x00007ff74d469ff3


# Test 7 is for Windows Server 2012 R2 with 32-bit js debug deterministic shell:
#     +205
#     25d80b01 cc              int     3
def test_CDBParserTestCrash7():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-7c-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

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
    assert crashInfo.registers["eax"] == 0x00c8a948
    assert crashInfo.registers["ebx"] == 0x0053e32c
    assert crashInfo.registers["ecx"] == 0x6802052b
    assert crashInfo.registers["edx"] == 0x00000000
    assert crashInfo.registers["esi"] == 0x25d8094b
    assert crashInfo.registers["edi"] == 0x0053e370
    assert crashInfo.registers["eip"] == 0x25d80b01
    assert crashInfo.registers["esp"] == 0x0053e370
    assert crashInfo.registers["ebp"] == 0xffe00000

    assert crashInfo.crashAddress == 0x25d80b01


def test_CDBSelectorTest7():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-7c-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x25d80b01


# Test 8 is for Windows Server 2012 R2 with 32-bit js debug profiling deterministic shell:
#     js_dbg_32_prof_dm_windows_42c95d88aaaa!js::jit::Range::upper+3d [
#         c:\users\administrator\trees\mozilla-central\js\src\jit\rangeanalysis.h @ 578]
#     0142865d cc              int     3
def test_CDBParserTestCrash8():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-8c-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

    assert len(crashInfo.backtrace) == 1
    assert crashInfo.backtrace[0] == "??"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["eax"] == 0x00000000
    assert crashInfo.registers["ebx"] == 0x00000000
    assert crashInfo.registers["ecx"] == 0x73f1705d
    assert crashInfo.registers["edx"] == 0x00ea9210
    assert crashInfo.registers["esi"] == 0x00000383
    assert crashInfo.registers["edi"] == 0x0a03d110
    assert crashInfo.registers["eip"] == 0x0142865d
    assert crashInfo.registers["esp"] == 0x00eaa780
    assert crashInfo.registers["ebp"] == 0x00eaa7ec

    assert crashInfo.crashAddress == 0x0142865d


def test_CDBSelectorTest8():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-8c-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x0142865d


# Test 9 is for Windows Server 2012 R2 with 32-bit js opt profiling shell:
#     +1d8
#     0f2bb4f3 cc              int     3
def test_CDBParserTestCrash9():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-9c-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

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
    assert crashInfo.registers["ebx"] == 0x00b0ea18
    assert crashInfo.registers["ecx"] == 0x00000400
    assert crashInfo.registers["edx"] == 0x73e74f80
    assert crashInfo.registers["esi"] == 0xffffff8c
    assert crashInfo.registers["edi"] == 0x00b0ea00
    assert crashInfo.registers["eip"] == 0x0f2bb4f3
    assert crashInfo.registers["esp"] == 0x00b0ea00
    assert crashInfo.registers["ebp"] == 0x00b0eab0

    assert crashInfo.crashAddress == 0x0f2bb4f3


def test_CDBSelectorTest9():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-9c-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x0f2bb4f3


# Test 10 is for Windows Server 2012 R2 with 32-bit js opt profiling shell:
#     +82
#     1c2fbbb0 cc              int     3
def test_CDBParserTestCrash10():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-10c-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

    assert len(crashInfo.backtrace) == 5
    assert crashInfo.backtrace[0] == "??"
    assert crashInfo.backtrace[1] == "js::jit::PrepareOsrTempData"
    assert crashInfo.backtrace[2] == "??"
    assert crashInfo.backtrace[3] == "js::AddTypePropertyId"
    assert crashInfo.backtrace[4] == "JSObject::makeLazyGroup"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["eax"] == 0x06fda948
    assert crashInfo.registers["ebx"] == 0x020de8dc
    assert crashInfo.registers["ecx"] == 0x5f7b6461
    assert crashInfo.registers["edx"] == 0x00000000
    assert crashInfo.registers["esi"] == 0x1c2fbaab
    assert crashInfo.registers["edi"] == 0x020de910
    assert crashInfo.registers["eip"] == 0x1c2fbbb0
    assert crashInfo.registers["esp"] == 0x020de910
    assert crashInfo.registers["ebp"] == 0x00000018

    assert crashInfo.crashAddress == 0x1c2fbbb0


def test_CDBSelectorTest10():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-10c-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x1c2fbbb0


# Test 11 is for Windows Server 2012 R2 with 32-bit js debug profiling deterministic shell:
#     js_dbg_32_prof_dm_windows_42c95d88aaaa!js::jit::Range::upper+3d [
#         c:\users\administrator\trees\mozilla-central\js\src\jit\rangeanalysis.h @ 578]
#     0156865d cc              int     3
def test_CDBParserTestCrash11():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-11c-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

    assert len(crashInfo.backtrace) == 1
    assert crashInfo.backtrace[0] == "??"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["eax"] == 0x00000000
    assert crashInfo.registers["ebx"] == 0x00000000
    assert crashInfo.registers["ecx"] == 0x738f705d
    assert crashInfo.registers["edx"] == 0x00e7b0e0
    assert crashInfo.registers["esi"] == 0x00000383
    assert crashInfo.registers["edi"] == 0x0ba37110
    assert crashInfo.registers["eip"] == 0x0156865d
    assert crashInfo.registers["esp"] == 0x00e7c650
    assert crashInfo.registers["ebp"] == 0x00e7c6bc

    assert crashInfo.crashAddress == 0x0156865d


def test_CDBSelectorTest11():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-11c-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x0156865d


# Test 12 is for Windows Server 2012 R2 with 32-bit js opt profiling deterministic shell:
#     +1d8
#     1fa0b7f8 cc              int     3
def test_CDBParserTestCrash12():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-12c-crashlog.txt'), 'r') as f:
        crashInfo = CDBCrashInfo([], [], config, f.read().splitlines())

    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "??"
    assert crashInfo.backtrace[1] == "??"
    assert crashInfo.backtrace[2] == "js::AddTypePropertyId"
    assert crashInfo.backtrace[3] == "JSObject::makeLazyGroup"

    assert crashInfo.crashInstruction == "int 3"
    assert crashInfo.registers["eax"] == 0x00000020
    assert crashInfo.registers["ebx"] == 0x0044ea78
    assert crashInfo.registers["ecx"] == 0x00000000
    assert crashInfo.registers["edx"] == 0x73bf4f80
    assert crashInfo.registers["esi"] == 0xffffff8c
    assert crashInfo.registers["edi"] == 0x0044ea50
    assert crashInfo.registers["eip"] == 0x1fa0b7f8
    assert crashInfo.registers["esp"] == 0x0044ea50
    assert crashInfo.registers["ebp"] == 0x0044eb00

    assert crashInfo.crashAddress == 0x1fa0b7f8


def test_CDBSelectorTest12():
    config = ProgramConfiguration("test", "x86", "windows")

    with open(os.path.join(CWD, 'resources', 'cdb-12c-crashlog.txt'), 'r') as f:
        crashData = f.read().splitlines()

    crashInfo = CrashInfo.fromRawCrashData([], [], config, crashData)
    assert crashInfo.crashAddress == 0x1fa0b7f8


def test_UBSanParserTestCrash1():
    config = ProgramConfiguration("test", "x86", "linux")
    crashInfo = CrashInfo.fromRawCrashData([], [], config, ubsanTraceSignedIntOverflow.splitlines())
    assert crashInfo.createShortSignature() == ("UndefinedBehaviorSanitizer: "
                                                "codec/decoder/core/inc/dec_golomb.h:182:37: "
                                                "runtime error: signed integer overflow: -2147483648 - "
                                                "1 cannot be represented in type 'int'")
    assert len(crashInfo.backtrace) == 12
    assert crashInfo.backtrace[0] == "WelsDec::BsGetUe"
    assert crashInfo.backtrace[9] == "_start"
    assert crashInfo.backtrace[11] == "Lex< >"
    assert crashInfo.crashAddress is None


def test_UBSanParserTestCrash2():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData([], [], config, ubsanTraceDivByZero.splitlines())
    assert crashInfo.createShortSignature() == ("UndefinedBehaviorSanitizer: src/opus_demo.c:870:40: "
                                                "runtime error: division by zero")
    assert len(crashInfo.backtrace) == 3
    assert crashInfo.backtrace[0] == "main"
    assert crashInfo.crashAddress is None


def test_UBSanParserTestCrash3():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData([], [], config, ubsanTraceMissingPattern.splitlines())
    assert crashInfo.createShortSignature() == "No crash detected"
    assert len(crashInfo.backtrace) == 0
    assert crashInfo.crashAddress is None


def test_UBSanParserTestCrash4():
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData([], [], config, ubsanTraceGenericCrash.splitlines())
    assert crashInfo.createShortSignature() == ("[@ mozilla::dom::ToJSValue]")
    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "mozilla::dom::ToJSValue"
    assert crashInfo.backtrace[1] == "js::jit::DoCallFallback"

    assert crashInfo.crashAddress == 0x000000004141
    assert crashInfo.registers["pc"] == 0x7f070b805037
    assert crashInfo.registers["bp"] == 0x7f06626006b0
    assert crashInfo.registers["sp"] == 0x7f0662600680


def test_RustParserTests1():
    """test RUST_BACKTRACE=1 is parsed correctly"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData([], [], config, rustSampleTrace1.splitlines())
    assert isinstance(crashInfo, RustCrashInfo)
    assert crashInfo.createShortSignature() == ("thread 'StyleThread#2' panicked at "
                                                "'assertion failed: self.get_data().is_some()', "
                                                "/home/worker/workspace/build/src/servo/components/"
                                                "style/gecko/wrapper.rs:976")
    assert len(crashInfo.backtrace) == 20
    assert crashInfo.backtrace[0] == "std::sys::imp::backtrace::tracing::imp::unwind_backtrace"
    assert crashInfo.backtrace[14] == ("<style::gecko::traversal::RecalcStyleOnly<'recalc> as "
                                       "style::traversal::DomTraversal<style::gecko::wrapper::"
                                       "GeckoElement<'le>>>::process_preorder")
    assert crashInfo.backtrace[19] == "<unknown>"
    assert crashInfo.crashAddress == 0


def test_RustParserTests2():
    """test RUST_BACKTRACE=full is parsed correctly"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData([], [], config, rustSampleTrace2.splitlines())
    assert isinstance(crashInfo, RustCrashInfo)
    assert crashInfo.createShortSignature() == ("thread 'StyleThread#3' panicked at "
                                                "'assertion failed: self.get_data().is_some()', "
                                                "/home/worker/workspace/build/src/servo/components/style/"
                                                "gecko/wrapper.rs:1040")
    assert len(crashInfo.backtrace) == 21
    assert crashInfo.backtrace[0] == "std::sys::imp::backtrace::tracing::imp::unwind_backtrace"
    assert crashInfo.backtrace[14] == ("<style::gecko::traversal::RecalcStyleOnly<'recalc> as "
                                       "style::traversal::DomTraversal<style::gecko::wrapper::"
                                       "GeckoElement<'le>>>::process_preorder")
    assert crashInfo.backtrace[20] == "<unknown>"
    assert crashInfo.crashAddress == 0
    crashInfo = CrashInfo.fromRawCrashData([], [], config, rustSampleTrace3.splitlines())
    assert isinstance(crashInfo, RustCrashInfo)
    assert crashInfo.createShortSignature() == ("thread 'StyleThread#2' panicked at "
                                                "'already mutably borrowed', /home/worker/workspace/build/"
                                                "src/third_party/rust/atomic_refcell/src/lib.rs:161")
    assert len(crashInfo.backtrace) == 7
    assert crashInfo.backtrace[0] == "std::sys::imp::backtrace::tracing::imp::unwind_backtrace"
    assert crashInfo.backtrace[3] == "std::panicking::rust_panic_with_hook"
    assert crashInfo.backtrace[6] == ("<style::values::specified::color::Color as style::values::computed"
                                      "::ToComputedValue>::to_computed_value")
    assert crashInfo.crashAddress == 0


def test_RustParserTests3():
    """test rust backtraces are weakly found, ie. minidump output wins even if it comes after"""
    config = ProgramConfiguration("test", "x86-64", "win")
    crashInfo = CrashInfo.fromRawCrashData([], [], config, rustSampleTrace4.splitlines())
    assert isinstance(crashInfo, MinidumpCrashInfo)
    assert crashInfo.createShortSignature() == (r"thread 'StyleThread#2' panicked at "
                                                r"'already mutably borrowed', "
                                                r"Z:\build\build\src\third_party\rust\atomic_"
                                                r"refcell\src\lib.rs:161")
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "std::panicking::rust_panic_with_hook"
    assert crashInfo.backtrace[1] == "std::panicking::begin_panic<&str>"
    assert crashInfo.backtrace[2] == "atomic_refcell::AtomicBorrowRef::do_panic"
    assert crashInfo.backtrace[3] == "style::values::specified::color::{{impl}}::to_computed_value"
    assert crashInfo.crashAddress == 0x7ffc41f2f276


def test_RustParserTests4():
    """test another rust backtrace"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData([], [], config, rustSampleTrace5.splitlines())
    assert isinstance(crashInfo, RustCrashInfo)
    assert crashInfo.createShortSignature() == ("thread 'RenderBackend' panicked at 'called "
                                                "`Option::unwrap()` on a `None` value', /checkout/src/"
                                                "libcore/option.rs:335:20")
    assert len(crashInfo.backtrace) == 3
    assert crashInfo.backtrace[0] == "std::sys::imp::backtrace::tracing::imp::unwind_backtrace"
    assert crashInfo.backtrace[1] == "std::panicking::default_hook::{{closure}}"
    assert crashInfo.backtrace[2] == "std::panicking::default_hook"
    assert crashInfo.crashAddress == 0


def test_RustParserTests5():
    """test multi-line with minidump trace in sterror rust backtrace"""
    auxData = ["OS|Linux|0.0.0 Linux ... x86_64",
               "CPU|amd64|family 6 model 63 stepping 2|8",
               "GPU|||",
               "Crash|SIGSEGV|0x0|0",
               ("0|0|firefox|mozalloc_abort|hg:hg.mozilla.org/mozilla-central:memory/mozalloc/mozalloc_abort.cpp:"
                "6d82e132348f|33|0x0"),
               ("0|1|firefox|abort|hg:hg.mozilla.org/mozilla-central:memory/mozalloc/mozalloc_abort.cpp:"
                "6d82e132348f|80|0x5"),
               ("0|2|libxul.so|panic_abort::__rust_start_panic|git:github.com/rust-lang/rust:src/libpanic_abort/"
                "lib.rs:05e2e1c41414e8fc73d0f267ea8dab1a3eeeaa99|59|0x5")]
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData([], rustSampleTrace6.splitlines(), config, auxData)
    assert isinstance(crashInfo, MinidumpCrashInfo)
    assert "panicked at 'assertion failed: `(left == right)`" in crashInfo.createShortSignature()
    assert len(crashInfo.backtrace) == 3
    assert crashInfo.backtrace[0] == "mozalloc_abort"
    assert crashInfo.backtrace[1] == "abort"
    assert crashInfo.backtrace[2] == "panic_abort::__rust_start_panic"
    assert crashInfo.crashAddress == 0


def test_RustParserTests6():
    """test parsing rust assertion failure backtrace"""
    config = ProgramConfiguration("test", "x86-64", "linux")
    crashInfo = CrashInfo.fromRawCrashData([], rustSampleTrace6.splitlines(), config, [])
    assert isinstance(crashInfo, RustCrashInfo)
    assert "panicked at 'assertion failed: `(left == right)`" in crashInfo.createShortSignature()
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[1] == "std::sys_common::backtrace::_print"
    assert crashInfo.crashAddress == 0


def test_MinidumpModuleInStackTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = CrashInfo.fromRawCrashData([], [], config, minidumpSwrast.splitlines())
    assert crashInfo.backtrace[0] == "??"
    assert crashInfo.backtrace[1] == "swrast_dri.so+0x470ecc"


def test_LSanParserTestLeakDetected():
    config = ProgramConfiguration("test", "x86-64", "linux")

    crashInfo = CrashInfo.fromRawCrashData([], [], config, lsanTraceLeakDetected.splitlines())
    assert crashInfo.createShortSignature() == ("LeakSanitizer: [@ malloc]")
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "malloc"
    assert crashInfo.backtrace[1] == "moz_xmalloc"
    assert crashInfo.backtrace[2] == "operator new"
    assert crashInfo.backtrace[3] == "mozilla::net::nsStandardURL::StartClone"
    assert crashInfo.crashAddress is None


def test_TSanParserSimpleLeakTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    with open(os.path.join(CWD, 'resources', 'tsan-simple-leak-report.txt'), 'r') as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == ("ThreadSanitizer: thread leak [@ pthread_create]")

    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "pthread_create"
    assert crashInfo.backtrace[1] == "main"

    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_TSanParserSimpleRaceTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    for fn in ['tsan-simple-race-report.txt', 'tsan-simple-race-report-swapped.txt']:
        with open(os.path.join(CWD, 'resources', fn), 'r') as f:
            crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

        assert crashInfo.createShortSignature() == ("ThreadSanitizer: data race [@ foo1] vs. [@ foo2]")

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

    with open(os.path.join(CWD, 'resources', 'tsan-lock-report.txt'), 'r') as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == (
        "ThreadSanitizer: lock-order-inversion (potential deadlock) [@ PR_Lock]")

    assert len(crashInfo.backtrace) == 12
    assert crashInfo.backtrace[0] == "pthread_mutex_lock"
    assert crashInfo.backtrace[1] == "PR_Lock"
    assert crashInfo.backtrace[2] == "sftk_hasAttribute"
    assert crashInfo.backtrace[3] == "sftk_CopyObject"
    assert crashInfo.backtrace[4] == "pthread_mutex_lock"

    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_TSanParserTest():
    config = ProgramConfiguration("test", "x86-64", "linux")

    with open(os.path.join(CWD, 'resources', 'tsan-report.txt'), 'r') as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == ("ThreadSanitizer: data race "
                                                "[@ js::ProtectedData<js::CheckMainThread"
                                                "<(js::AllowedHelperThread)0>, unsigned long>::operator++] "
                                                "vs. [@ js::gc::GCRuntime::majorGCCount]")

    assert len(crashInfo.backtrace) == 146
    assert crashInfo.backtrace[1] == "js::gc::GCRuntime::incMajorGcNumber"
    assert crashInfo.backtrace[5] == "js::gc::GCRuntime::gcIfNeededAtAllocation"

    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_ValgrindCJMParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-cjm-01.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == \
        "Valgrind: Conditional jump or move depends on uninitialised value(s) [@ PyObject_Free]"
    assert len(crashInfo.backtrace) == 7
    assert crashInfo.backtrace[0] == "PyObject_Free"
    assert crashInfo.backtrace[1] == "/usr/bin/python3.6"
    assert crashInfo.backtrace[3] == "main"
    assert crashInfo.backtrace[-1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None

    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-cjm-02.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == \
        "Valgrind: Conditional jump or move depends on uninitialised value(s) [@ strlen]"
    assert len(crashInfo.backtrace) == 5
    assert crashInfo.backtrace[0] == "strlen"
    assert crashInfo.backtrace[1] == "puts"
    assert crashInfo.backtrace[3] == "(below main)"
    assert crashInfo.backtrace[4] == "/home/user/a.out"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_ValgrindIRWParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-ir-01.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == "Valgrind: Invalid read of size 4 [@ blah_func]"
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "blah_func"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.backtrace[-1] == "asdf"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0xbadf00d

    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-ir-02.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == "Valgrind: Invalid read of size 4 [@ main]"
    assert len(crashInfo.backtrace) == 1
    assert crashInfo.backtrace[0] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0x5204068

    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-iw-01.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == "Valgrind: Invalid write of size 8 [@ memcpy]"
    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "memcpy"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0x41414141


def test_ValgrindUUVParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-uuv-01.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == "Valgrind: Use of uninitialised value of size 8 [@ foo<123>::Init]"
    assert len(crashInfo.backtrace) == 5
    assert crashInfo.backtrace[0] == "foo<123>::Init"
    assert crashInfo.backtrace[1], "bar::func<bar::Init()::$_0, Promise<type1, type2 == true> >::Run"
    assert crashInfo.backtrace[2] == "non-virtual thunk to Run"
    assert crashInfo.backtrace[-1] == "posix_memalign"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_ValgrindIFParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-if-01.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == "Valgrind: Invalid free() / delete / delete[] / realloc() [@ free]"
    assert len(crashInfo.backtrace) == 4
    assert crashInfo.backtrace[0] == "free"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.backtrace[-1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0x43f2931

    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-if-02.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == "Valgrind: Invalid free() / delete / delete[] / realloc() [@ free]"
    assert len(crashInfo.backtrace) == 6
    assert crashInfo.backtrace[0] == "free"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.backtrace[-1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0x5204040

    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-if-03.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == "Valgrind: Invalid free() / delete / delete[] / realloc() [@ free]"
    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "free"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0xbadf00d


def test_ValgrindSDOParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-sdo-01.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == "Valgrind: Source and destination overlap [@ memcpy]"
    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "memcpy"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_ValgrindSCParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-sc-01.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == \
        "Valgrind: Syscall param write(buf) points to uninitialised byte(s) [@ write]"
    assert len(crashInfo.backtrace) == 6
    assert crashInfo.backtrace[0] == "write"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.backtrace[-1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0x522e040

    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-sc-02.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == \
        "Valgrind: Syscall param socketcall.sendto(msg) points to uninitialised byte(s) [@ send]"
    assert len(crashInfo.backtrace) == 5
    assert crashInfo.backtrace[0] == "send"
    assert crashInfo.backtrace[2] == "start_thread"
    assert crashInfo.backtrace[-1] == "start_thread"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress == 0x5e7b6b4


def test_ValgrindNMParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-nm-01.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == \
        "Valgrind: Argument 'size' of function malloc has a fishy (possibly negative) value: -1 [@ malloc]"
    assert len(crashInfo.backtrace) == 2
    assert crashInfo.backtrace[0] == "malloc"
    assert crashInfo.backtrace[1] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_ValgrindPTParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-pt-01.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == \
        "Valgrind: Process terminating with default action of signal 11 (SIGSEGV) [@ strlen]"
    assert len(crashInfo.backtrace) == 3
    assert crashInfo.backtrace[0] == "strlen"
    assert crashInfo.backtrace[2] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None


def test_ValgrindLeakParser():
    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-leak-01.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == "Valgrind: 102,400 bytes in 1,024 blocks are definitely lost [@ malloc]"
    assert len(crashInfo.backtrace) == 3
    assert crashInfo.backtrace[0] == "malloc"
    assert crashInfo.backtrace[2] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None

    config = ProgramConfiguration("test", "x86-64", "linux")
    with open(os.path.join(CWD, "resources", "valgrind-leak-02.txt"), "r") as f:
        crashInfo = CrashInfo.fromRawCrashData([], [], config, f.read().splitlines())

    assert crashInfo.createShortSignature() == "Valgrind: 16 bytes in 1 blocks are possibly lost [@ malloc]"
    assert len(crashInfo.backtrace) == 3
    assert crashInfo.backtrace[0] == "malloc"
    assert crashInfo.backtrace[2] == "main"
    assert crashInfo.crashInstruction is None
    assert crashInfo.crashAddress is None
