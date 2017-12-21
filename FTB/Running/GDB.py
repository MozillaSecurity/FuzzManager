#!/usr/bin/env python
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


def is64bit():
    return not str(gdb.parse_and_eval("$rax")) == "void"  # @UndefinedVariable


def isARM():
    return not str(gdb.parse_and_eval("$r0")) == "void"  # @UndefinedVariable


def regAsHexStr(reg):
    if is64bit():
        mask = 0xffffffffffffffff
    else:
        mask = 0xffffffff
    return "0x%x" % (int(str(gdb.parse_and_eval("$" + reg)), 0) & mask)  # @UndefinedVariable


def regAsIntStr(reg):
    return str(int(str(gdb.parse_and_eval("$" + reg)), 0))  # @UndefinedVariable


def regAsRaw(reg):
    return str(gdb.parse_and_eval("$" + reg))  # @UndefinedVariable


def printImportantRegisters():
    if is64bit():
        regs = "rax rbx rcx rdx rsi rdi rbp rsp r8 r9 r10 r11 r12 r13 r14 r15 rip".split(" ")
    elif isARM():
        regs = "r0 r1 r2 r3 r4 r5 r6 r7 r8 r9 r10 r11 r12 sp lr pc cpsr".split(" ")
    else:
        regs = "eax ebx ecx edx esi edi ebp esp eip".split(" ")

    for reg in regs:
        try:
            print(reg + "\t" + regAsHexStr(reg) + "\t" + regAsIntStr(reg))
        except:
            print(reg + "\t" + regAsRaw(reg))
