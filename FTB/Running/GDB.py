# encoding: utf-8
'''
GDB - Contains functions directly used by GDB for crash processing

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
from __future__ import print_function


def is64bit():
    return not str(gdb.parse_and_eval("$rax")) == "void"  # noqa @UndefinedVariable


def isARM():
    return not str(gdb.parse_and_eval("$r0")) == "void"  # noqa @UndefinedVariable


def isARM64():
    return not str(gdb.parse_and_eval("$x0")) == "void"  # noqa @UndefinedVariable


def regAsHexStr(reg):
    if is64bit():
        mask = 0xffffffffffffffff
    else:
        mask = 0xffffffff
    return "0x%x" % (int(str(gdb.parse_and_eval("$" + reg)), 0) & mask)  # noqa @UndefinedVariable


def regAsIntStr(reg):
    return str(int(str(gdb.parse_and_eval("$" + reg)), 0))  # noqa @UndefinedVariable


def regAsRaw(reg):
    return str(gdb.parse_and_eval("$" + reg))  # noqa @UndefinedVariable


def printImportantRegisters():
    if is64bit():
        regs = "rax rbx rcx rdx rsi rdi rbp rsp r8 r9 r10 r11 r12 r13 r14 r15 rip".split(" ")
    elif isARM():
        regs = "r0 r1 r2 r3 r4 r5 r6 r7 r8 r9 r10 r11 r12 sp lr pc cpsr".split(" ")
    elif isARM64():
        # ARM64 has GPRs from x0 to x30
        regs = ["x" + str(x) for x in range(0, 31)]
        regs.extend("sp pc cpsr fpcsr fpcr".split(" "))
    else:
        regs = "eax ebx ecx edx esi edi ebp esp eip".split(" ")

    for reg in regs:
        try:
            print(reg + "\t" + regAsHexStr(reg) + "\t" + regAsIntStr(reg))
        except Exception:
            print(reg + "\t" + regAsRaw(reg))
