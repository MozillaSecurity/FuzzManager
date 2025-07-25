"""
AutoRunner -- Determine the correct runner class (GDB, ASan, etc) for
              the given program, instantiate and return it.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""

import os
import shutil
import subprocess
import sys
from abc import ABCMeta
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp

from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures.CrashInfo import CrashInfo, NoCrashInfo


class AutoRunner(metaclass=ABCMeta):
    """
    Abstract base class that provides a method to instantiate the right sub class
    for running the given program and obtaining crash information.
    """

    def __init__(self, binary, args=None, env=None, cwd=None, stdin=None):
        self.binary = binary
        self.cwd = cwd
        self.stdin = stdin

        if self.stdin and isinstance(self.stdin, list):
            self.stdin = "\n".join(self.stdin)

        # Certain debuggers like GDB can run into problems when certain
        # environment variables are missing. Hence we copy the system environment
        # variables by default and overwrite them if they are specified through env.
        self.env = dict(os.environ)
        if env:
            for envkey in env:
                self.env[envkey] = env[envkey]

        if "LD_LIBRARY_PATH" not in self.env:
            self.env["LD_LIBRARY_PATH"] = os.path.dirname(binary)

        self.args = args
        if self.args is None:
            self.args = []

        assert isinstance(self.env, dict)
        assert isinstance(self.args, list)

        # The command that we will run for obtaining crash information
        self.cmdArgs = []

        # These will hold our results from running
        self.stdout = None
        self.stderr = None
        self.auxCrashData = None

    def getCrashInfo(self, configuration):
        return CrashInfo.fromRawCrashData(
            self.stdout, self.stderr, configuration, self.auxCrashData
        )

    @staticmethod
    def fromBinaryArgs(binary, args=None, env=None, cwd=None, stdin=None):
        process = subprocess.Popen(
            ["nm", "-g", binary],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            env=env,
        )

        (stdout, _) = process.communicate()
        stdout = stdout.decode("utf-8", errors="ignore")

        force_gdb = bool(os.environ.get("FTB_FORCE_GDB", False))

        if not force_gdb and (
            stdout.find(" __asan_init") >= 0
            or stdout.find("__ubsan_default_options") >= 0
        ):
            return ASanRunner(binary, args, env, cwd, stdin)

        return GDBRunner(binary, args, env, cwd, stdin)


class GDBRunner(AutoRunner):
    def __init__(self, binary, args=None, env=None, cwd=None, core=None, stdin=None):
        AutoRunner.__init__(self, binary, args, env, cwd, stdin)

        # This can be used to force GDBRunner to first generate a core and then
        # also use it immediately for generating crash information. This is
        # required in the rare case that a crash doesn't reproduce then the
        # program runs directly under GDB.
        self.force_core = bool(os.environ.get("FTB_FORCE_GDBCORE", False))

        classPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GDB.py")
        self.gdbArgs = [
            "--batch",
            "-ex",
            f"source {classPath}",
        ]

        if core is None and not self.force_core:
            self.gdbArgs.extend(["-ex", "run"])

        self.gdbArgs.extend(
            [
                "-ex",
                "set pagination 0",
                "-ex",
                "set backtrace limit 128",
                "-ex",
                "bt",
                "-ex",
                "python printImportantRegisters()",
                "-ex",
                "x/2i $pc",
                "-ex",
                "quit",
            ]
        )

        if core is None and not self.force_core:
            self.gdbArgs.append("--args")

        self.cmdArgs.append("gdb")
        self.cmdArgs.extend(self.gdbArgs)
        self.cmdArgs.append(self.binary)

        if not self.force_core:
            if core is not None:
                self.cmdArgs.append(core)
            else:
                self.cmdArgs.extend(self.args)

    def run(self):
        if self.force_core:
            plainCmdArgs = [self.binary]
            plainCmdArgs.extend(self.args)

            process = subprocess.Popen(
                plainCmdArgs,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.cwd,
                env=self.env,
            )

            core = "core.%s" % process.pid

            (plainStdout, plainStderr) = process.communicate(input=self.stdin)

            if os.path.isfile(core):
                self.cmdArgs.append(core)
            elif os.path.isfile("core"):
                # Fallback in case core_uses_pid is disabled
                self.cmdArgs.append("core")
            else:
                print(
                    "Unable to locate core dump, check system configuration",
                    file=sys.stderr,
                )
                return False

        process = subprocess.Popen(
            self.cmdArgs,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
            env=self.env,
        )

        (stdout, stderr) = process.communicate(input=self.stdin)

        self.stdout = stdout.decode("utf-8", errors="ignore")
        self.stderr = stderr.decode("utf-8", errors="ignore")

        # Detect where the GDB trace starts/ends
        traceStart = self.stdout.rfind(" received signal SIG")
        traceStop = self.stdout.rfind("A debugging session is active")

        # Alternative GDB start version when using core dumps
        if traceStart < 0:
            traceStart = self.stdout.rfind("Program terminated with signal")

        if traceStart < 0:
            return False

        if traceStop < 0:
            traceStop = len(self.stdout)

        # Move the trace from stdout to auxCrashData
        self.auxCrashData = self.stdout[traceStart:traceStop]
        self.stdout = self.stdout[:traceStart] + self.stdout[traceStop:]

        # If we used the core dump method, use stdout/err from the first run
        if self.force_core:
            self.stdout = plainStdout.decode("utf-8", errors="ignore")
            self.stderr = plainStderr.decode("utf-8", errors="ignore")

        return True


class ASanRunner(AutoRunner):
    def __init__(self, binary, args=None, env=None, cwd=None, stdin=None):
        AutoRunner.__init__(self, binary, args, env, cwd, stdin)

        self.cmdArgs.append(self.binary)
        self.cmdArgs.extend(self.args)

        if "ASAN_SYMBOLIZER_PATH" not in self.env:
            if "ASAN_SYMBOLIZER_PATH" in os.environ:
                self.env["ASAN_SYMBOLIZER_PATH"] = os.environ["ASAN_SYMBOLIZER_PATH"]
            else:
                self.env["ASAN_SYMBOLIZER_PATH"] = os.path.join(
                    os.path.dirname(binary), "llvm-symbolizer"
                )
                if not os.path.isfile(self.env["ASAN_SYMBOLIZER_PATH"]):
                    self.env["ASAN_SYMBOLIZER_PATH"] = shutil.which("llvm-symbolizer")
                    if not self.env["ASAN_SYMBOLIZER_PATH"]:
                        raise RuntimeError("Unable to locate llvm-symbolizer")

        if not os.path.isfile(self.env["ASAN_SYMBOLIZER_PATH"]):
            raise RuntimeError(
                "Misconfigured ASAN_SYMBOLIZER_PATH: "
                f"{self.env['ASAN_SYMBOLIZER_PATH']}"
            )

        if "UBSAN_OPTIONS" not in self.env:
            if "UBSAN_OPTIONS" in os.environ:
                self.env["UBSAN_OPTIONS"] = os.environ["UBSAN_OPTIONS"]
            else:
                # Default to print stacktraces and summary if no other options are set.
                # If the caller overrides these options, they need to set this
                # themselves, otherwise this code won't be able to isolate a UBSan
                # trace.
                self.env["UBSAN_OPTIONS"] = "print_stacktrace=1:print_summary=1"

        if "ASAN_OPTIONS" not in self.env:
            if "ASAN_OPTIONS" in os.environ:
                self.env["ASAN_OPTIONS"] = os.environ["ASAN_OPTIONS"]
            else:
                # Default to allowing the allocator to return null to reproduce crashes
                # mostly caused by OOM conditions rather than aborting with the ASan OOM
                # failure. If ASAN_OPTIONS is already set, then the caller should ensure
                # that this option is present.
                # handle_abort is set to true to use the ASan to print the stack trace
                # for bucketing. This is helpful when assertions are hit in debug builds
                self.env["ASAN_OPTIONS"] = "allocator_may_return_null=1:handle_abort=1"

    def run(self):
        tmpd = Path(mkdtemp(prefix="fm-autorun-"))
        try:
            env = self.env.copy()
            env["ASAN_OPTIONS"] = f"{env.get('ASAN_OPTIONS', '')}:log_path={tmpd}/crash"
            env["UBSAN_OPTIONS"] = (
                f"{env.get('UBSAN_OPTIONS', '')}:log_path={tmpd}/crash"
            )
            env["TSAN_OPTIONS"] = f"{env.get('TSAN_OPTIONS', '')}:log_path={tmpd}/crash"

            # create a ProgramConfiguration just to create the temporary CrashInfo
            pc = ProgramConfiguration.fromBinary(self.binary)
            process = subprocess.run(
                self.cmdArgs,
                stdin=self.stdin,
                capture_output=True,
                text=True,
                cwd=self.cwd,
                env=env,
            )

            self.stdout = process.stdout
            self.stderr = process.stderr
            first = True
            self.auxCrashData = []
            for crash in tmpd.iterdir():
                self.auxCrashData = crash.read_text()
                if not first:
                    print(
                        "warning: multiple sanitizer logs detected",
                        file=sys.stderr,
                    )
                first = False
        finally:
            rmtree(tmpd)

        crash_info = CrashInfo.fromRawCrashData(
            self.stdout, self.stderr, pc, self.auxCrashData
        )
        if isinstance(crash_info, NoCrashInfo):
            return False

        return True
