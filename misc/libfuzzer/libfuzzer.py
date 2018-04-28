#!/usr/bin/env python
# encoding: utf-8
'''
libfuzzer -- Simple script to manage libfuzzer processes

This script serves as a harness around a libfuzzer binary, monitoring its
state, restarting it when necessary and submitting crashes to FuzzManager.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

import argparse
import os
import subprocess
import sys
import threading

from Collector.Collector import Collector  # noqa
from FTB.ProgramConfiguration import ProgramConfiguration  # noqa
from FTB.Signatures.CrashInfo import CrashInfo  # noqa


class LibFuzzerMonitor(threading.Thread):
    def __init__(self, fd):
        assert callable(fd.readline)

        threading.Thread.__init__(self)

        self.fd = fd
        self.trace = []
        self.inTrace = False
        self.testcase = None

    def run(self):
        while True:
            line = self.fd.readline(4096)

            if not line:
                break

            if self.inTrace:
                self.trace.append(line.rstrip())
                if line.find("==ABORTING") >= 0:
                    self.inTrace = False
            elif line.find("==ERROR: AddressSanitizer") >= 0:
                self.trace.append(line.rstrip())
                self.inTrace = True

            if line.find("Test unit written to ") >= 0:
                self.testcase = line.split()[-1]

            # Pass-through output
            sys.stderr.write(line)

        self.fd.close()

    def getASanTrace(self):
        return self.trace

    def getTestcase(self):
        return self.testcase


__all__ = []
__version__ = 0.1
__date__ = '2016-07-28'
__updated__ = '2016-07-28'


def main(argv=None):
    '''Command line options.'''

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = "%s" % __updated__

    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)

    if argv is None:
        argv = sys.argv[1:]

    # setup argparser
    parser = argparse.ArgumentParser(usage='%s [OPTIONS] --cmd <COMMAND AND ARGUMENTS>' % program_name)

    mainGroup = parser.add_argument_group(title="Main arguments", description=None)
    fmGroup = parser.add_argument_group(title="FuzzManager specific options",
                                        description="""Values for the options listed here are typically
                                                    provided through FuzzManager configuration files,
                                                    but can be overwritten using these options:""")

    mainGroup.add_argument('--version', action='version', version=program_version_string)
    mainGroup.add_argument('--cmd', dest='cmd', action='store_true', help="Command with parameters to run")
    mainGroup.add_argument('--env', dest='env', nargs='+', type=str,
                           help="List of environment variables in the form 'KEY=VALUE'")

    # Settings
    fmGroup.add_argument("--sigdir", dest="sigdir", help="Signature cache directory", metavar="DIR")
    fmGroup.add_argument("--serverhost", dest="serverhost", help="Server hostname for remote signature management",
                         metavar="HOST")
    fmGroup.add_argument("--serverport", dest="serverport", type=int, help="Server port to use", metavar="PORT")
    fmGroup.add_argument("--serverproto", dest="serverproto", help="Server protocol to use (default is https)",
                         metavar="PROTO")
    fmGroup.add_argument("--serverauthtokenfile", dest="serverauthtokenfile",
                         help="File containing the server authentication token", metavar="FILE")
    fmGroup.add_argument("--clientid", dest="clientid", help="Client ID to use when submitting issues", metavar="ID")
    fmGroup.add_argument("--platform", dest="platform",
                         help="Platform this crash appeared on", metavar="(x86|x86-64|arm)")
    fmGroup.add_argument("--product", dest="product", help="Product this crash appeared on", metavar="PRODUCT")
    fmGroup.add_argument("--productversion", dest="product_version", help="Product version this crash appeared on",
                         metavar="VERSION")
    fmGroup.add_argument("--os", dest="os", help="OS this crash appeared on",
                         metavar="(windows|linux|macosx|b2g|android)")
    fmGroup.add_argument("--tool", dest="tool", help="Name of the tool that found this issue", metavar="NAME")
    fmGroup.add_argument('--metadata', dest='metadata', nargs='+', type=str,
                         help="List of metadata variables in the form 'KEY=VALUE'")

    parser.add_argument('rargs', nargs=argparse.REMAINDER, help=argparse.SUPPRESS)

    if len(argv) == 0:
        parser.print_help()
        return 2

    # process options
    opts = parser.parse_args(argv)

    if not opts.rargs:
        print("Error: No arguments specified", file=sys.stderr)
        return 2

    binary = opts.rargs[0]
    if not os.path.exists(binary):
        print("Error: Specified binary does not exist: %s" % binary, file=sys.stderr)
        return 2

    configuration = ProgramConfiguration.fromBinary(binary)
    if configuration is None:
        print("Error: Failed to load program configuration based on binary", file=sys.stderr)
        return 2

        if opts.platform is None or opts.product is None or opts.os is None:
            print(("Error: Must use binary configuration file or specify/configure at least "
                   "--platform, --product and --os"), file=sys.stderr)
            return 2

        configuration = ProgramConfiguration(opts.product, opts.platform, opts.os, opts.product_version)

    env = {}
    if opts.env:
        env = dict(kv.split('=', 1) for kv in opts.env)
        configuration.addEnvironmentVariables(env)

    # Copy the system environment variables by default and overwrite them
    # if they are specified through env.
    env = dict(os.environ)
    if opts.env:
        oenv = dict(kv.split('=', 1) for kv in opts.env)
        configuration.addEnvironmentVariables(oenv)
        for envkey in oenv:
            env[envkey] = oenv[envkey]

    args = opts.rargs[1:]
    if args:
        configuration.addProgramArguments(args)

    metadata = {}
    if opts.metadata:
        metadata.update(dict(kv.split('=', 1) for kv in opts.metadata))
        configuration.addMetadata(metadata)

    # Set LD_LIBRARY_PATH for convenience
    if 'LD_LIBRARY_PATH' not in env:
        env['LD_LIBRARY_PATH'] = os.path.dirname(binary)

    serverauthtoken = None
    if opts.serverauthtokenfile:
        with open(opts.serverauthtokenfile) as f:
            serverauthtoken = f.read().rstrip()

    collector = Collector(opts.sigdir, opts.serverhost, opts.serverport, opts.serverproto, serverauthtoken,
                          opts.clientid, opts.tool)

    signature_repeat_count = 0
    last_signature = None

    while(True):
        process = subprocess.Popen(
            opts.rargs,
            # stdout=None,
            stderr=subprocess.PIPE,
            env=env,
            universal_newlines=True
        )

        monitor = LibFuzzerMonitor(process.stderr)
        monitor.start()
        monitor.join()

        print("Process terminated, processing results...", file=sys.stderr)

        trace = monitor.getASanTrace()
        testcase = monitor.getTestcase()

        crashInfo = CrashInfo.fromRawCrashData([], [], configuration, auxCrashData=trace)

        (sigfile, metadata) = collector.search(crashInfo)

        if sigfile is not None:
            if last_signature == sigfile:
                signature_repeat_count += 1
            else:
                last_signature = sigfile
                signature_repeat_count = 0

            print("Crash matches signature %s, not submitting..." % sigfile, file=sys.stderr)
        else:
            collector.generate(crashInfo, forceCrashAddress=True, forceCrashInstruction=False, numFrames=8)
            collector.submit(crashInfo, testcase)
            print("Successfully submitted crash.", file=sys.stderr)

        if signature_repeat_count >= 10:
            print("Too many crashes with the same signature, exiting...", file=sys.stderr)
            break


if __name__ == "__main__":
    sys.exit(main())
