"""
GDB - Contains functions directly used by GDB for crash processing

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import gdb  # noqa: TC004


def is64bit() -> bool:
    return str(gdb.parse_and_eval("$rax")) != "void"


def isARM() -> bool:
    return str(gdb.parse_and_eval("$r0")) != "void"


def isARM64() -> bool:
    return str(gdb.parse_and_eval("$x0")) != "void"


def regAsHexStr(reg: str) -> str:
    mask = 0xFFFFFFFFFFFFFFFF if is64bit() else 0xFFFFFFFF
    val = int(str(gdb.parse_and_eval("$" + reg)), 0) & mask
    return f"0x{val:x}"


def regAsIntStr(reg: str) -> str:
    return str(int(str(gdb.parse_and_eval("$" + reg)), 0))


def regAsRaw(reg: str) -> str:
    return str(gdb.parse_and_eval("$" + reg))


def printImportantRegisters() -> None:
    if is64bit():
        regs = [
            "rax",
            "rbx",
            "rcx",
            "rdx",
            "rsi",
            "rdi",
            "rbp",
            "rsp",
            "r8",
            "r9",
            "r10",
            "r11",
            "r12",
            "r13",
            "r14",
            "r15",
            "rip",
        ]
    elif isARM():
        regs = [
            "r0",
            "r1",
            "r2",
            "r3",
            "r4",
            "r5",
            "r6",
            "r7",
            "r8",
            "r9",
            "r10",
            "r11",
            "r12",
            "sp",
            "lr",
            "pc",
            "cpsr",
        ]
    elif isARM64():
        # ARM64 has GPRs from x0 to x30
        regs = ["x" + str(x) for x in range(31)]
        regs.extend(["sp", "pc", "cpsr", "fpcsr", "fpcr"])
    else:
        regs = ["eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp", "eip"]

    for reg in regs:
        try:
            print(reg + "\t" + regAsHexStr(reg) + "\t" + regAsIntStr(reg))
        except Exception:  # noqa: PERF203
            print(reg + "\t" + regAsRaw(reg))
