'''
Helper methods around registers

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

x86Registers = ["eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "esp", "eip"]

x64Registers = ["rax", "rbx", "rcx", "rdx", "rsi", "rdi", "rbp", "rsp", "r8",
                "r9", "r10", "r11", "r12", "r13", "r14", "r15", "rip"]

armRegisters = ["r0", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "r8", "r9",
                "r10", "r11", "r12", "sp", "lr", "pc", "cpsr"]

arm64Registers = ["x" + str(x) for x in range(0, 31)] + ["sp", "pc", "cpsr", "fpcsr", "fpcr"]

x86OnlyRegisters = list(set(x86Registers + x64Registers) - set(armRegisters + arm64Registers))
armOnlyRegisters = list(set(armRegisters + arm64Registers) - set(x86Registers + x64Registers))

validRegisters = {
    "X86": x86Registers,
    "X64": x64Registers,
    "ARM": armRegisters,
    "ARM64": arm64Registers
}


def getRegisterPattern():
    '''
        Return a pattern including all register names that are considered valid
    '''
    return "(" + '|'.join(["%s"] * len(validRegisters)) % tuple(
        ['|'.join(i) for i in validRegisters.values()]) + ")"


def getStackPointer(registerMap):
    '''
        Return the stack pointer value from the given register map

        @type registerMap: map
        @param registerMap: Map of register names to value

        @rtype: int
        @return: The value of the stack pointer
    '''

    for reg in ["rsp", "esp", "sp"]:
        if reg in registerMap:
            return registerMap[reg]

    raise RuntimeError("Register map does not contain a usable stack pointer!")


def getInstructionPointer(registerMap):
    '''
        Return the instruction pointer value from the given register map

        @type registerMap: map
        @param registerMap: Map of register names to value

        @rtype: int
        @return: The value of the instruction pointer
    '''

    for reg in ["rip", "eip", "pc"]:
        if reg in registerMap:
            return registerMap[reg]

    raise RuntimeError("Register map does not contain a usable instruction pointer!")


def getRegisterValue(register, registerMap):
    '''
        Return the value of the specified register using the provided register map.
        This method also works for getting lower register parts out of higher ones.

        @type register: string
        @param register: The register to get the value for

        @type registerMap: map
        @param registerMap: Map of register names to values

        @rtype: int
        @return: The register value
    '''

    # If the register is requested as in the map, return it immediately
    if register in registerMap:
        return registerMap[register]

    if register.startswith("e"):
        # We might have the case that 32 bit of a 64 bit register
        # are requested (e.g. eax and we have rax). Either that is
        # the case, or we return None anyway because we don't know
        # what else to do.
        higherRegister = register.replace("e", "r", 1)
        if higherRegister in registerMap:
            return registerMap[higherRegister] & 0xFFFFFFFF

    if register.startswith("w"):
        # In this case, likely the lower 32-bit of a 64-bit ARM64
        # register are requested, so we rewrite this similarly to x86-64.
        higherRegister = register.replace("w", "x", 1)
        if higherRegister in registerMap:
            return registerMap[higherRegister] & 0xFFFFFFFF

    if len(register) == 2:
        # We're either requesting the lower 16 bit of a register (ax),
        # or higher/lower 8 bit of the lower 16 bit register (ah/al).
        if register.endswith("x"):
            # Find proper higher register
            reg32 = "e" + register
            if reg32 in registerMap:
                return registerMap[reg32] & 0xFFFF

            reg64 = "r" + register
            if reg64 in registerMap:
                return registerMap[reg64] & 0xFFFF
        elif register.endswith("h"):
            higherRegister = register.replace("h", "x", 1)
            # Find proper higher register
            reg32 = "e" + higherRegister
            if reg32 in registerMap:
                return (registerMap[reg32] & 0xFF00) >> 8

            reg64 = "r" + higherRegister
            if reg64 in registerMap:
                return (registerMap[reg64] & 0xFF00) >> 8
        elif register.endswith("l"):
            higherRegister = register.replace("l", "x", 1)
            # Find proper higher register
            reg32 = "e" + higherRegister
            if reg32 in registerMap:
                return registerMap[reg32] & 0xFF

            reg64 = "r" + higherRegister
            if reg64 in registerMap:
                return registerMap[reg64] & 0xFF

    return None


def getBitWidth(registerMap):
    '''
        Return the bit width (32 or 64 bit) given the registers

        @type registerMap: map
        @param registerMap: Map of register names to value

        @rtype: int
        @return: The bit width
    '''
    if "rax" in registerMap or "x0" in registerMap:
        return 64

    return 32


def isX86Compatible(registerMap):
    '''
        Return true, if the the given registers are X86 compatible, such as x86 or x86-64.
        ARM, PPC and your PDP-15 will fail this check and we don't support it right now.

        @type registerMap: map
        @param registerMap: Map of register names to value

        @rtype: bool
        @return: True if the architecture is X86 compatible, False otherwise
    '''
    for register in x86OnlyRegisters:
        if register in registerMap:
            return True
    return False


def isARMCompatible(registerMap):
    '''
        Return true, if the the given registers are either ARM or ARM64.

        @type registerMap: map
        @param registerMap: Map of register names to value

        @rtype: bool
        @return: True if the architecture is ARM/ARM64 compatible, False otherwise
    '''
    for register in armOnlyRegisters:
        if register in registerMap:
            return True
    return False
