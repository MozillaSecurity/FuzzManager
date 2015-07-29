#!/usr/bin/env python
# encoding: utf-8
'''
AFL Management Daemon -- Tool to manage AFL queue and results

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

import sys
import os
import argparse
import time

from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Running.AutoRunner import AutoRunner
from Collector.Collector import Collector

def scan_crashes(base_dir):
    crash_dir = os.path.join(base_dir, "crashes")
    crash_files = []

    for crash_file in os.listdir(crash_dir):
        # Ignore all files that aren't crash results
        if not crash_file.startswith("id:"):
            continue
        
        crash_file = os.path.join(crash_dir, crash_file)

        # Ignore our own status files
        if crash_file.endswith(".submitted") or crash_file.endswith(".failed"):
            continue
        
        # Ignore files we already processed
        if os.path.exists(crash_file + ".submitted") or os.path.exists(crash_file + ".failed"):
            continue
        
        crash_files.append(crash_file)
        
    if crash_files:
        # First try to read necessary information for reproducing crashes
        cmdline = []
        test_idx = None
        with open(os.path.join(base_dir, "cmdline"), 'r') as cmdline_file:
            idx = 0
            for line in cmdline_file:
                if '@@' in cmdline:
                    test_idx = idx
                cmdline.append(line.rstrip('\n'))
                idx += 1
            
        if test_idx != None:
            orig_test_arg = cmdline[test_idx]

        print(cmdline)
        
        configuration = ProgramConfiguration.fromBinary(cmdline[0])
        if not configuration:
            print("Error: Creating program configuration from binary failed. Check your binary configuration file.", file=sys.stderr)
            return 2
        
        collector = Collector()
        
        for crash_file in crash_files:
            stdin = None
            
            if test_idx != None:
                cmdline[test_idx] = orig_test_arg.replace('@@', crash_file)
            else:
                with open(crash_file, 'r') as crash_fd:
                    stdin = crash_fd.read()
            
            runner = AutoRunner.fromBinaryArgs(cmdline[0], cmdline[1:], stdin=stdin)
            if runner.run():
                crash_info = runner.getCrashInfo(configuration)
                collector.submit(crash_info, crash_file)
                open(crash_file + ".submitted", 'a').close()
            else:
                open(crash_file + ".failed", 'a').close()
                print("Error: Failed to reproduce the given crash, cannot submit.", file=sys.stderr)

def main(argv=None):
    '''Command line options.'''

    program_name = os.path.basename(sys.argv[0])

    if argv is None:
        argv = sys.argv[1:]

    # setup argparser
    parser = argparse.ArgumentParser()

    parser.add_argument("--s3", dest="s3config", help="Use S3 to synchronize queues", metavar="CONFIG")
    parser.add_argument("--fuzzmanager", dest="fuzzmanager", action='store_true', help="Use FuzzManager to submit crash results")
    parser.add_argument("--afl-dir", dest="afldir", help="Path to the AFL output directory to manage", metavar="DIR")

    parser.add_argument('rargs', nargs=argparse.REMAINDER)

    if len(argv) == 0:
        parser.print_help()
        return 2

    # process options
    opts = parser.parse_args(argv)
    
    if not opts.afldir:
        print("Error: Must specify AFL output directory using --afl-dir", file=sys.stderr)
        return 2

    if opts.s3config:
        print("Error: Not yet implemented", file=sys.stderr)
        return 2

    while True:
        if opts.fuzzmanager:
            scan_crashes(opts.afldir)
        
        time.sleep(10)

if __name__ == "__main__":
    sys.exit(main())
