#!/usr/bin/env python3
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

from Collector.Collector import Collector
from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Running.AutoRunner import AutoRunner
from FTB.Signatures.CrashInfo import CrashInfo

from S3Manager import S3Manager

import argparse
import collections
from fasteners import InterProcessLock
import os
import re
import shutil
from six.moves import queue
import stat
import subprocess
import sys
import tempfile
import threading
import time
import traceback

haveFFPuppet = True
try:
    from ffpuppet import FFPuppet
except ImportError:
    haveFFPuppet = False

RE_LIBFUZZER_STATUS = re.compile(r"\s*#(\d+)\s+(INITED|NEW|RELOAD|REDUCE|pulse)\s+cov:")
RE_LIBFUZZER_NEWPC = re.compile(r"\s+NEW_PC:\s+0x")
RE_LIBFUZZER_EXECS = re.compile(r"\s+exec/s: (\d+)\s+")
RE_LIBFUZZER_RSS = re.compile(r"\s+rss: (\d+)Mb")

# Used to set initialized to true, as the INITED message is not present with an empty corpus
NO_CORPUS_MSG = "INFO: A corpus is not provided, starting from an empty corpus"


class LibFuzzerMonitor(threading.Thread):
    def __init__(self, process, killOnOOM=True, mid=None, mqueue=None):
        threading.Thread.__init__(self)

        self.process = process
        self.fd = process.stderr
        self.trace = []
        self.stderr = collections.deque([], 128)
        self.inTrace = False
        self.testcase = None
        self.killOnOOM = killOnOOM
        self.hadOOM = False
        self.hitThreadLimit = False
        self.inited = False
        self.mid = mid
        self.mqueue = mqueue

        # Keep some statistics
        self.execs_done = 0
        self.execs_per_sec = 0
        self.rss_mb = 0
        self.last_new = 0
        self.last_new_pc = 0

        # Store potential exceptions
        self.exc = None

    def run(self):
        assert(not self.hitThreadLimit)
        assert(not self.hadOOM)

        try:
            while True:
                line = self.fd.readline(4096)

                if not line:
                    break

                status_match = RE_LIBFUZZER_STATUS.search(line)

                if status_match:
                    self.execs_done = int(status_match.group(1))

                    if status_match.group(2) == "NEW":
                        self.last_new = int(time.time())

                    exec_match = RE_LIBFUZZER_EXECS.search(line)
                    rss_match = RE_LIBFUZZER_RSS.search(line)

                    if exec_match:
                        self.execs_per_sec = int(exec_match.group(1))
                    if rss_match:
                        self.rss_mb = int(rss_match.group(1))
                elif RE_LIBFUZZER_NEWPC.search(line):
                    self.last_new_pc = int(time.time())
                elif self.inTrace:
                    self.trace.append(line.rstrip())
                    if line.find("==ABORTING") >= 0:
                        self.inTrace = False
                elif line.find("==ERROR: AddressSanitizer") >= 0:
                    self.trace.append(line.rstrip())
                    self.inTrace = True
                elif line.find("==AddressSanitizer: Thread limit") >= 0:
                    self.hitThreadLimit = True

                if not self.inTrace:
                    self.stderr.append(line)

                if not self.inited and (line.find("INITED cov") >= 0 or line.find(NO_CORPUS_MSG) >= 0):
                    self.inited = True

                if line.find("Test unit written to ") >= 0:
                    self.testcase = line.split()[-1]

                # libFuzzer sometimes hangs on out-of-memory. Kill it
                # right away if we detect this situation.
                if self.killOnOOM and line.find("ERROR: libFuzzer: out-of-memory") >= 0:
                    self.hadOOM = True
                    self.process.kill()

                # Pass-through output
                if self.mid is not None:
                    sys.stderr.write("[Job %s] %s" % (self.mid, line))
                else:
                    sys.stderr.write(line)

            self.fd.close()

            if self.hitThreadLimit and self.testcase and os.path.exists(self.testcase):
                # If we hit ASan's global thread limit, ignore the error and remove
                # the resulting testcase, as it won't be useful anyway.
                # Not that this thread limit is not a concurrent thread limit, but
                # a limit imposed on the number of threads ever started during the lifetime
                # of the process.
                os.remove(self.testcase)
                self.testcase = None
        except Exception as e:
            self.exc = e
        finally:
            if self.mqueue is not None:
                self.mqueue.put(self.mid)

    def getASanTrace(self):
        return self.trace

    def getTestcase(self):
        return self.testcase

    def getStderr(self):
        return list(self.stderr)

    def terminate(self):
        print("[Job %s] Received terminate request..." % self.mid, file=sys.stderr)

        # Avoid sending anything through the queue when the run() loop exits
        self.mqueue = None
        self.process.terminate()

        # Emulate a wait() with timeout through poll and sleep
        (maxSleepTime, pollInterval) = (10, 0.2)
        while self.process.poll() is None and maxSleepTime > 0:
            maxSleepTime -= pollInterval
            time.sleep(pollInterval)

        # Process is still alive, kill it and wait
        if self.process.poll() is None:
            self.process.kill()
            self.process.wait()


def command_file_to_list(cmd_file):
    '''
    Open and parse custom command line file

    @type cmd_file: String
    @param cmd_file: Command line file containing list of commands

    @rtype: Tuple
    @return: Test index in list and the command as a list of strings
    '''
    cmdline = list()
    idx = 0
    test_idx = None
    with open(cmd_file, 'r') as cmd_fp:
        for line in cmd_fp:
            if '@@' in line:
                test_idx = idx
            cmdline.append(line.rstrip())
            idx += 1

    return test_idx, cmdline


def write_stats_file(outfile, fields, stats, warnings):
    '''
    Write the given stats data to the specified file

    @type outfile: str
    @param outfile: Output file for statistics

    @type fields: list
    @param fields: The list of fields to write out (defines the order as well)

    @type stats: dict
    @param stats: The dictionary containing the actual data

    @type warnings: list
    @param warnings: Any textual warnings to write in addition to stats
    '''

    max_keylen = max(len(x) for x in fields)

    with InterProcessLock(outfile + ".lock"), open(outfile, 'w') as f:
        for field in fields:
            if field not in stats:
                continue

            val = stats[field]

            if isinstance(val, list):
                val = " ".join(val)

            f.write("%s%s: %s\n" % (field, " " * (max_keylen + 1 - len(field)), val))

        for warning in warnings:
            f.write(warning)

    return


def write_aggregated_stats_afl(base_dirs, outfile, cmdline_path=None):
    '''
    Generate aggregated statistics from the given base directories
    and write them to the specified output file.

    @type base_dirs: list
    @param base_dirs: List of AFL base directories

    @type outfile: str
    @param outfile: Output file for aggregated statistics

    @type cmdline_path: String
    @param cmdline_path: Optional command line file to use instead of the
                         one found inside the base directory.
    '''

    # Which fields to add
    wanted_fields_total = [
        'execs_done',
        'execs_per_sec',
        'pending_favs',
        'pending_total',
        'variable_paths',
        'unique_crashes',
        'unique_hangs']

    # Which fields to aggregate by mean
    wanted_fields_mean = ['exec_timeout']

    # Which fields should be displayed per fuzzer instance
    wanted_fields_all = ['cycles_done', 'bitmap_cvg']

    # Which fields should be aggregated by max
    wanted_fields_max = ['last_path']

    # Generate total list of fields to write
    fields = []
    fields.extend(wanted_fields_total)
    fields.extend(wanted_fields_mean)
    fields.extend(wanted_fields_all)
    fields.extend(wanted_fields_max)

    # Warnings to include
    warnings = list()

    aggregated_stats = {}

    for field in wanted_fields_total:
        aggregated_stats[field] = 0

    for field in wanted_fields_mean:
        aggregated_stats[field] = (0, 0)

    for field in wanted_fields_all:
        aggregated_stats[field] = []

    def convert_num(num):
        if '.' in num:
            return float(num)
        return int(num)

    for base_dir in base_dirs:
        stats_path = os.path.join(base_dir, "fuzzer_stats")

        if not cmdline_path:
            cmdline_path = os.path.join(base_dir, "cmdline")

        if os.path.exists(stats_path):
            with open(stats_path, 'r') as stats_file:
                stats = stats_file.read()

            for line in stats.splitlines():
                (field_name, field_val) = line.split(':', 1)
                field_name = field_name.strip()
                field_val = field_val.strip()

                if field_name in wanted_fields_total:
                    aggregated_stats[field_name] += convert_num(field_val)
                elif field_name in wanted_fields_mean:
                    (val, cnt) = aggregated_stats[field_name]
                    aggregated_stats[field_name] = (val + convert_num(field_val), cnt + 1)
                elif field_name in wanted_fields_all:
                    aggregated_stats[field_name].append(field_val)
                elif field_name in wanted_fields_max:
                    num_val = convert_num(field_val)
                    if (field_name not in aggregated_stats) or aggregated_stats[field_name] < num_val:
                        aggregated_stats[field_name] = num_val

    # If we don't have any data here, then the fuzzers haven't written any statistics yet
    if not aggregated_stats:
        return

    # Mean conversion
    for field_name in wanted_fields_mean:
        (val, cnt) = aggregated_stats[field_name]
        if cnt:
            aggregated_stats[field_name] = float(val) / float(cnt)
        else:
            aggregated_stats[field_name] = val

    # Verify fuzzmanagerconf exists and can be parsed
    _, cmdline = command_file_to_list(cmdline_path)
    target_binary = cmdline[0] if cmdline else None

    if target_binary is not None:
        if not os.path.isfile("%s.fuzzmanagerconf" % target_binary):
            warnings.append("WARNING: Missing %s.fuzzmanagerconf\n" % target_binary)
        elif ProgramConfiguration.fromBinary(target_binary) is None:
            warnings.append("WARNING: Invalid %s.fuzzmanagerconf\n" % target_binary)

    # Look for unreported crashes
    failed_reports = 0
    for base_dir in base_dirs:
        crashes_dir = os.path.join(base_dir, "crashes")
        if not os.path.isdir(crashes_dir):
            continue
        for crash_file in os.listdir(crashes_dir):
            if crash_file.endswith(".failed"):
                failed_reports += 1
    if failed_reports:
        warnings.append("WARNING: Unreported crashes detected (%d)\n" % failed_reports)

    # Write out data
    return write_stats_file(outfile, fields, aggregated_stats, warnings)


def write_aggregated_stats_libfuzzer(outfile, stats, monitors, warnings):
    '''
    Generate aggregated statistics for the given overall libfuzzer stats and the individual monitors.
    Results are written to the specified output file.

    @type outfile: str
    @param outfile: Output file for aggregated statistics

    @type stats: dict
    @param stats: Dictionary containing overall stats

    @type monitors: list
    @param monitors: A list of LibFuzzerMonitor instances

    @type warnings: list
    @param warnings: Any textual warnings to write in addition to stats
    '''

    # Which fields to add
    wanted_fields_total = [
        'execs_done',
        'execs_per_sec',
        'rss_mb',
        'corpus_size',
        'next_auto_reduce',
        'crashes',
        'timeouts',
        'ooms'
    ]

    # Which fields to aggregate by mean
    wanted_fields_mean = []

    # Which fields should be displayed per fuzzer instance
    wanted_fields_all = []

    # Which fields should be aggregated by max
    wanted_fields_max = ['last_new', 'last_new_pc']

    # This is a list of fields mentioned in one of the lists above already,
    # that should *additionally* also be aggregated with the global state.
    # Only supported for total and max aggregation.
    wanted_fields_global_aggr = [
        'execs_done',
        'last_new',
        'last_new_pc'
    ]

    # Generate total list of fields to write
    fields = []
    fields.extend(wanted_fields_total)
    fields.extend(wanted_fields_mean)
    fields.extend(wanted_fields_all)
    fields.extend(wanted_fields_max)

    aggregated_stats = {}

    # In certain cases, e.g. when exiting, one or more monitors can be down.
    monitors = [monitor for monitor in monitors if monitor is not None]

    if monitors:
        for field in wanted_fields_total:
            if hasattr(monitors[0], field):
                aggregated_stats[field] = 0
                for monitor in monitors:
                    aggregated_stats[field] += getattr(monitor, field)
                if field in wanted_fields_global_aggr:
                    aggregated_stats[field] += stats[field]
            else:
                # Assume global field
                aggregated_stats[field] = stats[field]

        for field in wanted_fields_mean:
            assert hasattr(monitors[0], field), "Field %s not in monitor" % field
            aggregated_stats[field] = 0
            for monitor in monitors:
                aggregated_stats[field] += getattr(monitor, field)
            aggregated_stats[field] = float(aggregated_stats[field]) / float(len(monitors))

        for field in wanted_fields_all:
            assert hasattr(monitors[0], field), "Field %s not in monitor" % field
            aggregated_stats[field] = []
            for monitor in monitors:
                aggregated_stats[field].append(getattr(monitor, field))

        for field in wanted_fields_max:
            assert hasattr(monitors[0], field), "Field %s not in monitor" % field
            aggregated_stats[field] = 0
            for monitor in monitors:
                val = getattr(monitor, field)
                if val > aggregated_stats[field]:
                    aggregated_stats[field] = val
            if field in wanted_fields_global_aggr and stats[field] > aggregated_stats[field]:
                aggregated_stats[field] = stats[field]

        for field in wanted_fields_global_aggr:
            # Write aggregated stats back into the global stats for max fields
            if field in wanted_fields_max:
                stats[field] = aggregated_stats[field]

    # Write out data
    return write_stats_file(outfile, fields, aggregated_stats, warnings)


def scan_crashes(base_dir, collector, cmdline_path=None, env_path=None, test_path=None, firefox=None,
                 firefox_prefs=None, firefox_extensions=None, firefox_testpath=None):
    '''
    Scan the base directory for crash tests and submit them to FuzzManager.

    @type base_dir: String
    @param base_dir: AFL base directory

    @type cmdline_path: String
    @param cmdline_path: Optional command line file to use instead of the
                         one found inside the base directory.

    @type env_path: String
    @param env_path: Optional file containing environment variables.

    @type test_path: String
    @param test_path: Optional filename where to copy the test before
                      attempting to reproduce a crash.

    @rtype: int
    @return: Non-zero return code on failure
    '''
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

        base_env = {}
        test_in_env = None
        if env_path:
            with open(env_path, 'r') as env_file:
                for line in env_file:
                    (name, val) = line.rstrip('\n').split("=", 1)
                    base_env[name] = val

                    if '@@' in val:
                        test_in_env = name

        if not cmdline_path:
            cmdline_path = os.path.join(base_dir, "cmdline")

        test_idx, cmdline = command_file_to_list(cmdline_path)
        if test_idx is not None:
            orig_test_arg = cmdline[test_idx]

        configuration = ProgramConfiguration.fromBinary(cmdline[0])
        if not configuration:
            print("Error: Creating program configuration from binary failed."
                  "Check your binary configuration file.", file=sys.stderr)
            return 2

        if firefox:
            (ffpInst, ffCmd, ffEnv) = setup_firefox(cmdline[0], firefox_prefs, firefox_extensions, firefox_testpath)
            cmdline = ffCmd
            base_env.update(ffEnv)

        for crash_file in crash_files:
            stdin = None
            env = None

            if base_env:
                env = dict(base_env)

            if test_idx is not None:
                cmdline[test_idx] = orig_test_arg.replace('@@', crash_file)
            elif test_in_env is not None:
                env[test_in_env] = env[test_in_env].replace('@@', crash_file)
            elif test_path is not None:
                shutil.copy(crash_file, test_path)
            else:
                with open(crash_file, 'r') as crash_fd:
                    stdin = crash_fd.read()

            print("Processing crash file %s" % crash_file, file=sys.stderr)

            runner = AutoRunner.fromBinaryArgs(cmdline[0], cmdline[1:], env=env, stdin=stdin)
            if runner.run():
                crash_info = runner.getCrashInfo(configuration)
                collector.submit(crash_info, crash_file)
                open(crash_file + ".submitted", 'a').close()
                print("Success: Submitted crash to server.", file=sys.stderr)
            else:
                open(crash_file + ".failed", 'a').close()
                print("Error: Failed to reproduce the given crash, cannot submit.", file=sys.stderr)

        if firefox:
            ffpInst.clean_up()


def setup_firefox(bin_path, prefs_path, ext_paths, test_path):
    ffp = FFPuppet(use_xvfb=True)

    # For now we support only one extension, but FFPuppet will handle
    # multiple extensions soon.
    ext_path = None
    if ext_paths:
        ext_path = ext_paths[0]

    ffp.profile = ffp.create_profile(extension=ext_path, prefs_js=prefs_path)

    env = ffp.get_environ(bin_path)
    cmd = ffp.build_launch_cmd(bin_path, additional_args=[test_path])

    try:
        # Remove any custom ASan options passed by FFPuppet as they might
        # interfere with AFL. This should be removed once we can ensure
        # that options passed by FFPuppet work with AFL.
        del env['ASAN_OPTIONS']
    except KeyError:
        pass

    return (ffp, cmd, env)


def test_binary_asan(bin_path):
    process = subprocess.Popen(
        ["nm", "-g", bin_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    (stdout, _) = process.communicate()

    if stdout.find(b" __asan_init") >= 0 or stdout.find(b"__ubsan_default_options") >= 0:
        return True
    return False


def main(argv=None):
    '''Command line options.'''

    program_name = os.path.basename(sys.argv[0])

    if argv is None:
        argv = sys.argv[1:]

    # setup argparser
    parser = argparse.ArgumentParser(usage='%s --libfuzzer or --aflfuzz [OPTIONS] --cmd <COMMAND AND ARGUMENTS>'
                                     % program_name)

    mainGroup = parser.add_argument_group(title="Main Options", description=None)
    aflGroup = parser.add_argument_group(title="AFL Options", description="Use these arguments in AFL mode.")
    libfGroup = parser.add_argument_group(title="Libfuzzer Options",
                                          description="Use these arguments in Libfuzzer mode.")
    fmGroup = parser.add_argument_group(title="FuzzManager Options",
                                        description="Use these to specify or override FuzzManager parameters."
                                        " Most of these parameters are typically specified in the global FuzzManager"
                                        " configuration file.")
    s3Group = parser.add_argument_group(title="AWS S3 Options", description="Use these arguments for various S3 actions"
                                        " and parameters related to operating libFuzzer/AFL within AWS and managing"
                                        " build, corpus and progress in S3.")

    fmOrLocalGroup = mainGroup.add_mutually_exclusive_group()
    fmOrLocalGroup.add_argument("--fuzzmanager", dest="fuzzmanager", action='store_true',
                                help="Use FuzzManager to submit crash results")
    fmOrLocalGroup.add_argument("--local", dest="local", action='store_true',
                                help="Don't submit crash results anywhere (default)")

    mainGroup.add_argument("--libfuzzer", dest="libfuzzer", action='store_true', help="Enable libFuzzer mode")
    mainGroup.add_argument("--aflfuzz", dest="aflfuzz", action='store_true', help="Enable AFL mode")
    mainGroup.add_argument("--debug", dest="debug", action='store_true',
                           help="Shows useful debug information (e.g. disables command output suppression)")
    mainGroup.add_argument("--stats", dest="stats",
                           help="Collect aggregated statistics in specified file", metavar="FILE")

    s3Group.add_argument("--s3-queue-upload", dest="s3_queue_upload", action='store_true',
                         help="Use S3 to synchronize queues")
    s3Group.add_argument("--s3-queue-cleanup", dest="s3_queue_cleanup", action='store_true',
                         help="Cleanup S3 closed queues.")
    s3Group.add_argument("--s3-queue-status", dest="s3_queue_status", action='store_true',
                         help="Display S3 queue status")
    s3Group.add_argument("--s3-build-download", dest="s3_build_download",
                         help="Use S3 to download the build for the specified project", metavar="DIR")
    s3Group.add_argument("--s3-build-upload", dest="s3_build_upload",
                         help="Use S3 to upload a new build for the specified project", metavar="FILE")
    s3Group.add_argument("--s3-corpus-download", dest="s3_corpus_download",
                         help="Use S3 to download the test corpus for the specified project", metavar="DIR")
    s3Group.add_argument("--s3-corpus-download-size", dest="s3_corpus_download_size",
                         help="When downloading the corpus, select only SIZE files randomly", metavar="SIZE")
    s3Group.add_argument("--s3-corpus-upload", dest="s3_corpus_upload",
                         help="Use S3 to upload a test corpus for the specified project", metavar="DIR")
    s3Group.add_argument("--s3-corpus-replace", dest="s3_corpus_replace", action='store_true',
                         help="In conjunction with --s3-corpus-upload, deletes all other remote test files")
    s3Group.add_argument("--s3-corpus-refresh", dest="s3_corpus_refresh",
                         help="Download queues and corpus from S3, combine and minimize, then re-upload.",
                         metavar="DIR")
    s3Group.add_argument("--s3-corpus-status", dest="s3_corpus_status", action='store_true',
                         help="Display S3 corpus status")
    s3Group.add_argument("--s3-bucket", dest="s3_bucket", help="Name of the S3 bucket to use", metavar="NAME")
    s3Group.add_argument("--project", dest="project", help="Name of the subfolder/project inside the S3 bucket",
                         metavar="NAME")
    s3Group.add_argument("--build", dest="build",
                         help="Local build directory to use during corpus refresh instead of downloading.",
                         metavar="DIR")
    s3Group.add_argument("--build-project", dest="build_project",
                         help="If specified, this overrides --project for fetching the build from S3.",
                         metavar="NAME")
    s3Group.add_argument("--build-zip-name", dest="build_zip_name", default="build.zip",
                         help="Override default build.zip name when working with S3 builds.",
                         metavar="NAME")

    libfGroup.add_argument('--env', dest='env', nargs='+', type=str,
                           help="List of environment variables in the form 'KEY=VALUE'")
    libfGroup.add_argument('--cmd', dest='cmd', action='store_true', help="Command with parameters to run")
    libfGroup.add_argument("--libfuzzer-restarts", dest="libfuzzer_restarts", type=int,
                           help="Maximum number of restarts to do with libFuzzer", metavar="COUNT")
    libfGroup.add_argument("--libfuzzer-instances", dest="libfuzzer_instances", type=int, default=1,
                           help="Number of parallel libfuzzer instances to run", metavar="COUNT")
    libfGroup.add_argument("--libfuzzer-auto-reduce", dest="libfuzzer_auto_reduce", type=int,
                           help="Auto-reduce the corpus once it has grown by this percentage", metavar="PERCENT")
    libfGroup.add_argument("--libfuzzer-auto-reduce-min", dest="libfuzzer_auto_reduce_min", type=int, default=1000,
                           help="Minimum corpus size for auto-reduce to apply.", metavar="COUNT")

    fmGroup.add_argument("--custom-cmdline-file", dest="custom_cmdline_file", help="Path to custom cmdline file",
                         metavar="FILE")
    fmGroup.add_argument("--env-file", dest="env_file", help="Path to a file with additional environment variables",
                         metavar="FILE")
    fmGroup.add_argument("--serverhost", dest="serverhost", help="Server hostname for remote signature management.",
                         metavar="HOST")
    fmGroup.add_argument("--serverport", dest="serverport", type=int, help="Server port to use", metavar="PORT")
    fmGroup.add_argument("--serverproto", dest="serverproto", help="Server protocol to use (default is https)",
                         metavar="PROTO")
    fmGroup.add_argument("--serverauthtokenfile", dest="serverauthtokenfile",
                         help="File containing the server authentication token", metavar="FILE")
    fmGroup.add_argument("--clientid", dest="clientid", help="Client ID to use when submitting issues", metavar="ID")
    fmGroup.add_argument("--platform", dest="platform", help="Platform this crash appeared on",
                         metavar="(x86|x86-64|arm)")
    fmGroup.add_argument("--product", dest="product", help="Product this crash appeared on", metavar="PRODUCT")
    fmGroup.add_argument("--productversion", dest="product_version", help="Product version this crash appeared on",
                         metavar="VERSION")
    fmGroup.add_argument("--os", dest="os", help="OS this crash appeared on",
                         metavar="(windows|linux|macosx|b2g|android)")
    fmGroup.add_argument("--tool", dest="tool", help="Name of the tool that found this issue", metavar="NAME")
    fmGroup.add_argument('--metadata', dest='metadata', nargs='+', type=str,
                         help="List of metadata variables in the form 'KEY=VALUE'")
    fmGroup.add_argument("--sigdir", dest="sigdir", help="Signature cache directory", metavar="DIR")

    aflGroup.add_argument("--test-file", dest="test_file",
                          help="Optional path to copy the test file to before reproducing", metavar="FILE")
    aflGroup.add_argument("--afl-timeout", dest="afl_timeout", type=int, default=1000,
                          help="Timeout per test to pass to AFL for corpus refreshing", metavar="MSECS")
    aflGroup.add_argument("--firefox", dest="firefox", action='store_true',
                          help="Test Program is Firefox (requires FFPuppet installed)")
    aflGroup.add_argument("--firefox-prefs", dest="firefox_prefs",
                          help="Path to prefs.js file for Firefox", metavar="FILE")
    aflGroup.add_argument("--firefox-extensions", nargs='+', type=str, dest="firefox_extensions",
                          help="Path extension file for Firefox", metavar="FILE")
    aflGroup.add_argument("--firefox-testpath", dest="firefox_testpath", help="Path to file to open with Firefox",
                          metavar="FILE")
    aflGroup.add_argument("--firefox-start-afl", dest="firefox_start_afl", metavar="FILE",
                          help="Start AFL with the given Firefox binary, remaining arguments being passed to AFL")
    aflGroup.add_argument("--afl-output-dir", dest="afloutdir", help="Path to the AFL output directory to manage",
                          metavar="DIR")
    aflGroup.add_argument("--afl-binary-dir", dest="aflbindir", help="Path to the AFL binary directory to use",
                          metavar="DIR")
    aflGroup.add_argument("--afl-stats", dest="aflstats",
                          help="Deprecated, use --stats instead", metavar="FILE")
    aflGroup.add_argument('rargs', nargs=argparse.REMAINDER)

    def warn_local():
        if not opts.fuzzmanager and not opts.local:
            # User didn't specify --fuzzmanager but also didn't specify --local explicitly, so we should warn them
            # that their crash results won't end up anywhere except on the local machine. This method is called for
            # AFL and libFuzzer separately whenever it is determined that the user is running fuzzing locally.
            print("Warning: You are running in local mode, crashes won't be submitted anywhere...", file=sys.stderr)
            time.sleep(2)

    if not argv:
        parser.print_help()
        return 2

    opts = parser.parse_args(argv)

    if opts.aflstats:
        print("Error: --afl-stats is deprecated, use --stats instead.", file=sys.stderr)
        time.sleep(2)

    if not opts.libfuzzer and not opts.aflfuzz:
        # For backwards compatibility, --aflfuzz is the default if nothing else is specified.
        opts.aflfuzz = True

    if opts.libfuzzer and opts.aflfuzz:
        print("Error: --libfuzzer and --aflfuzz are mutually exclusive.", file=sys.stderr)
        return 2

    if opts.fuzzmanager:
        serverauthtoken = None
        if opts.serverauthtokenfile:
            with open(opts.serverauthtokenfile) as f:
                serverauthtoken = f.read().rstrip()

        collector = Collector(sigCacheDir=opts.sigdir, serverHost=opts.serverhost, serverPort=opts.serverport,
                              serverProtocol=opts.serverproto, serverAuthToken=serverauthtoken,
                              clientId=opts.clientid, tool=opts.tool)

    # ## Begin generic S3 action handling ##

    s3m = None

    if (opts.s3_queue_upload or opts.s3_corpus_refresh or opts.s3_build_download or opts.s3_build_upload or
            opts.s3_corpus_download or opts.s3_corpus_upload or opts.s3_queue_status or opts.s3_corpus_status or
            opts.s3_queue_cleanup):
        if not opts.s3_bucket or not opts.project:
            print("Error: Must specify both --s3-bucket and --project for S3 actions", file=sys.stderr)
            return 2

        s3m = S3Manager(opts.s3_bucket, opts.project, opts.build_project, opts.build_zip_name)

    if opts.s3_queue_status:
        status_data = s3m.get_queue_status()
        total_queue_files = 0

        for queue_name in status_data:
            print("Queue %s: %s" % (queue_name, status_data[queue_name]))
            total_queue_files += status_data[queue_name]
        print("Total queue files: %s" % total_queue_files)

        return 0

    if opts.s3_corpus_status:
        status_data = s3m.get_corpus_status()
        total_corpus_files = 0

        for (status_dt, status_cnt) in sorted(status_data.items()):
            print("Added %s: %s" % (status_dt, status_cnt))
            total_corpus_files += status_cnt
        print("Total corpus files: %s" % total_corpus_files)

        return 0

    if opts.s3_queue_cleanup:
        s3m.clean_queue_dirs()
        return 0

    if opts.s3_build_download:
        s3m.download_build(opts.s3_build_download)
        return 0

    if opts.s3_build_upload:
        s3m.upload_build(opts.s3_build_upload)
        return 0

    if opts.s3_corpus_download:
        if opts.s3_corpus_download_size is not None:
            opts.s3_corpus_download_size = int(opts.s3_corpus_download_size)

        s3m.download_corpus(opts.s3_corpus_download, opts.s3_corpus_download_size)
        return 0

    if opts.s3_corpus_upload:
        s3m.upload_corpus(opts.s3_corpus_upload, opts.s3_corpus_replace)
        return 0

    if opts.s3_corpus_refresh:
        if opts.aflfuzz and not opts.aflbindir:
            print("Error: Must specify --afl-binary-dir for refreshing the test corpus", file=sys.stderr)
            return 2

        if not os.path.exists(opts.s3_corpus_refresh):
            os.makedirs(opts.s3_corpus_refresh)

        queues_dir = os.path.join(opts.s3_corpus_refresh, "queues")

        print("Cleaning old queues from s3://%s/%s/queues/" % (opts.s3_bucket, opts.project))
        s3m.clean_queue_dirs()

        print("Downloading queues from s3://%s/%s/queues/ to %s" % (opts.s3_bucket, opts.project, queues_dir))
        s3m.download_queue_dirs(opts.s3_corpus_refresh)

        cmdline_file = os.path.join(opts.s3_corpus_refresh, "cmdline")
        if not os.path.exists(cmdline_file):
            # this can happen in a few legitimate cases:
            #  - project folder does not exist at all (new project)
            #  - only closed queues existed (old project)
            #  - no queues exist (recently refreshed manually)
            # print the error, but return 0
            print("Error: Failed to download a cmdline file from queue directories.", file=sys.stderr)
            return 0

        build_path = os.path.join(opts.s3_corpus_refresh, "build")

        if opts.build:
            build_path = opts.build
        else:
            print("Downloading build")
            s3m.download_build(build_path)

        with open(os.path.join(opts.s3_corpus_refresh, "cmdline"), 'r') as cmdline_file:
            cmdline = cmdline_file.read().splitlines()

        # Assume cmdline[0] is the name of the binary
        binary_name = os.path.basename(cmdline[0])

        # Try locating our binary in the build we just unpacked
        binary_search_result = [os.path.join(dirpath, filename)
                                for dirpath, dirnames, filenames in
                                os.walk(build_path)
                                for filename in filenames
                                if (filename == binary_name and
                                (stat.S_IXUSR & os.stat(os.path.join(dirpath, filename))[stat.ST_MODE]))]

        if not binary_search_result:
            print("Error: Failed to locate binary %s in unpacked build." % binary_name, file=sys.stderr)
            return 2

        if len(binary_search_result) > 1:
            print("Error: Binary name %s is ambiguous in unpacked build." % binary_name, file=sys.stderr)
            return 2

        cmdline[0] = binary_search_result[0]

        # Download our current corpus into the queues directory as well
        print("Downloading corpus from s3://%s/%s/corpus/ to %s" % (opts.s3_bucket, opts.project, queues_dir))
        s3m.download_corpus(queues_dir)

        # Ensure the directory for our new tests is empty
        updated_tests_dir = os.path.join(opts.s3_corpus_refresh, "tests")
        if os.path.exists(updated_tests_dir):
            shutil.rmtree(updated_tests_dir)
        os.mkdir(updated_tests_dir)

        if opts.aflfuzz:
            # Run afl-cmin
            afl_cmin = os.path.join(opts.aflbindir, "afl-cmin")
            if not os.path.exists(afl_cmin):
                print("Error: Unable to locate afl-cmin binary.", file=sys.stderr)
                return 2

            if opts.firefox:
                (ffpInst, ffCmd, ffEnv) = setup_firefox(cmdline[0], opts.firefox_prefs, opts.firefox_extensions,
                                                        opts.firefox_testpath)
                cmdline = ffCmd

            afl_cmdline = [afl_cmin, '-e', '-i', queues_dir, '-o', updated_tests_dir, '-t', str(opts.afl_timeout),
                           '-m', 'none']

            if opts.test_file:
                afl_cmdline.extend(['-f', opts.test_file])

            afl_cmdline.extend(cmdline)

            print("Running afl-cmin")
            with open(os.devnull, 'w') as devnull:
                env = os.environ.copy()
                env['LD_LIBRARY_PATH'] = os.path.dirname(cmdline[0])

                if opts.firefox:
                    env.update(ffEnv)

                if opts.debug:
                    devnull = None
                subprocess.check_call(afl_cmdline, stdout=devnull, env=env)

            if opts.firefox:
                ffpInst.clean_up()
        else:
            cmdline.extend(["-merge=1", updated_tests_dir, queues_dir])

            # Filter out any -dict arguments that we don't need anyway for merging
            cmdline = [x for x in cmdline if not x.startswith("-dict=")]

            # Filter out any -max_len arguments because the length should only be
            # enforced by the instance(s) doing the actual testing.
            cmdline = [x for x in cmdline if not x.startswith("-max_len=")]

            print("Running libFuzzer merge")
            with open(os.devnull, 'w') as devnull:
                env = os.environ.copy()
                env['LD_LIBRARY_PATH'] = os.path.dirname(cmdline[0])
                if opts.debug:
                    devnull = None
                subprocess.check_call(cmdline, stdout=devnull, env=env)

        if not os.listdir(updated_tests_dir):
            print("Error: Merge returned empty result, refusing to upload.")
            return 2

        # replace existing corpus with reduced corpus
        print("Uploading reduced corpus to s3://%s/%s/corpus/" % (opts.s3_bucket, opts.project))
        s3m.upload_corpus(updated_tests_dir, corpus_delete=True)

        # Prune the queues directory once we successfully uploaded the new
        # test corpus, but leave everything that's part of our new corpus
        # so we don't have to download those files again.
        test_files = [file for file in os.listdir(updated_tests_dir)
                      if os.path.isfile(os.path.join(updated_tests_dir, file))]
        obsolete_queue_files = [file for file in os.listdir(queues_dir)
                                if os.path.isfile(os.path.join(queues_dir, file)) and file not in test_files]

        for file in obsolete_queue_files:
            os.remove(os.path.join(queues_dir, file))

        return 0

    # ## End generic S3 action handling ##

    if opts.cmd and opts.aflfuzz:
        if not opts.firefox:
            print("Error: Use --cmd either with libfuzzer or with afl in firefox mode", file=sys.stderr)
            return 2

    if opts.libfuzzer:
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

        # Build our libFuzzer command line. We add certain parameters automatically for convenience.
        cmdline = []
        cmdline.extend(opts.rargs)
        cmdline_add_args = []
        if test_binary_asan(binary):
            # With ASan, we always want to disable the internal signal handlers libFuzzer uses.
            cmdline_add_args.extend([
                "-handle_segv=0",
                "-handle_bus=0",
                "-handle_abrt=0",
                "-handle_ill=0",
                "-handle_fpe=0"
            ])
        else:
            # We currently don't support non-ASan binaries because the logic in LibFuzzerMonitor
            # expects an ASan trace on crash and CrashInfo doesn't parse internal libFuzzer traces.
            print("Error: This wrapper currently only supports binaries built with AddressSanitizer.", file=sys.stderr)
            return 2

        for arg in cmdline:
            if arg.startswith("-jobs=") or arg.startswith("-workers="):
                print("Error: Using -jobs and -workers is incompatible with this wrapper.", file=sys.stderr)
                print("       You can use --libfuzzer-instances to run multiple instances instead.", file=sys.stderr)
                return 2

        # Used by statistics and useful in general
        cmdline_add_args.append("-print_pcs=1")

        # Append args if they don't exist already
        for arg in cmdline_add_args:
            if arg not in cmdline:
                cmdline.append(arg)

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

        signature_repeat_count = 0
        last_signature = None
        last_queue_upload = 0
        restarts = opts.libfuzzer_restarts

        # The base directory for libFuzzer is the current working directory
        base_dir = os.getcwd()

        # Find the first corpus directory from our command line
        corpus_dir = None
        for rarg in opts.rargs:
            if os.path.isdir(rarg):
                corpus_dir = os.path.abspath(rarg)
                break

        if corpus_dir is None:
            print("Error: Failed to find a corpus directory on command line.", file=sys.stderr)
            return 2

        # At this point we know that we will be running libFuzzer locally
        warn_local()

        # Memorize the original corpus, so we can exclude it from uploading later
        original_corpus = set(os.listdir(corpus_dir))

        corpus_auto_reduce_threshold = None
        corpus_auto_reduce_ratio = None
        if opts.libfuzzer_auto_reduce is not None:
            if opts.libfuzzer_auto_reduce < 5:
                print("Error: Auto reduce threshold should at least be 5%.", file=sys.stderr)
                return 2

            corpus_auto_reduce_ratio = float(opts.libfuzzer_auto_reduce) / float(100)

            if len(original_corpus) >= opts.libfuzzer_auto_reduce_min:
                corpus_auto_reduce_threshold = int(len(original_corpus) * (1 + corpus_auto_reduce_ratio))
            else:
                # Corpus is smaller than --libfuzzer-auto-reduce-min specifies, so we calculate
                # the threshold based on that value in combination with the ratio instead, initially.
                corpus_auto_reduce_threshold = int(opts.libfuzzer_auto_reduce_min * (1 + corpus_auto_reduce_ratio))

            if corpus_auto_reduce_threshold <= len(original_corpus):
                print("Error: Invalid auto reduce threshold specified.", file=sys.stderr)
                return 2

        # Write a cmdline file, similar to what our AFL fork does
        with open("cmdline", 'w') as fd:
            for rarg in opts.rargs:
                # Omit any corpus directory that is in the command line
                if not os.path.isdir(rarg):
                    print(rarg, file=fd)

        monitors = [None] * opts.libfuzzer_instances
        monitor_queue = queue.Queue()

        # Keep track how often we crash to abort in certain situations
        crashes_per_minute_interval = 0
        crashes_per_minute = 0

        # Global stats
        stats = {
            "crashes": 0,
            "crashes_per_minute": 0,
            "timeouts": 0,
            "ooms": 0,
            "corpus_size": len(original_corpus),
            "execs_done": 0,
            "last_new": 0,
            "last_new_pc": 0,
            "next_auto_reduce": 0
        }

        # Memorize if we just did a corpus reduction, for S3 sync
        corpus_reduction_done = False

        # Memorize which corpus files we deleted (e.g. for timing out),
        # as this can happen in multiple subprocesses at once.
        removed_corpus_files = set()

        try:
            while True:
                if restarts is not None and restarts < 0 and all(x is None for x in monitors):
                    print("Run completed.", file=sys.stderr)
                    break

                # Check if we need to (re)start any monitors
                for i in range(len(monitors)):
                    if monitors[i] is None:
                        if restarts is not None:
                            restarts -= 1
                            if restarts < 0:
                                break

                        process = subprocess.Popen(
                            cmdline,
                            # stdout=None,
                            stderr=subprocess.PIPE,
                            env=env,
                            universal_newlines=True
                        )

                        monitors[i] = LibFuzzerMonitor(process, mid=i, mqueue=monitor_queue)
                        monitors[i].start()

                corpus_size = None
                if corpus_auto_reduce_threshold is not None or opts.stats:
                    # We need the corpus size for stats and the auto reduce feature,
                    # so we cache it here to avoid running listdir multiple times.
                    corpus_size = len(os.listdir(corpus_dir))

                if corpus_auto_reduce_threshold is not None and corpus_size >= corpus_auto_reduce_threshold:
                    print("Preparing automated merge...", file=sys.stderr)

                    # Time to Auto-reduce
                    for i in range(len(monitors)):
                        monitor = monitors[i]
                        if monitor is not None:
                            print("Asking monitor %s to terminate..." % i, file=sys.stderr)
                            monitor.terminate()
                            monitor.join(30)
                            if monitor.is_alive():
                                raise RuntimeError("Monitor refusing to stop.")

                            # Indicate that this monitor is dead, so it is restarted later on
                            monitors[i] = None

                            if opts.stats:
                                # Make sure the execs that this monitor did survive in stats
                                stats["execs_done"] += monitor.execs_done

                    # All monitors are assumed to be dead now, clear the monitor queue in case
                    # it has remaining ids from monitors that terminated on their own before
                    # we terminated them.
                    while not monitor_queue.empty():
                        monitor_queue.get_nowait()

                    merge_cmdline = []
                    merge_cmdline.extend(cmdline)

                    # Filter all directories on the command line, these are likely corpus dirs
                    merge_cmdline = [x for x in merge_cmdline if not os.path.isdir(x)]

                    # Filter out other stuff we don't want for merging
                    merge_cmdline = [x for x in merge_cmdline if not x.startswith("-dict=")]

                    new_corpus_dir = tempfile.mkdtemp(prefix="fm-libfuzzer-automerge-")
                    merge_cmdline.extend(["-merge=1", new_corpus_dir, corpus_dir])

                    print("Running automated merge...", file=sys.stderr)
                    with open(os.devnull, 'w') as devnull:
                        env = os.environ.copy()
                        env['LD_LIBRARY_PATH'] = os.path.dirname(merge_cmdline[0])
                        if opts.debug:
                            devnull = None
                        subprocess.check_call(merge_cmdline, stdout=devnull, env=env)

                    if not os.listdir(new_corpus_dir):
                        print("Error: Merge returned empty result, refusing to continue.")
                        return 2

                    shutil.rmtree(corpus_dir)
                    shutil.move(new_corpus_dir, corpus_dir)

                    # Update our corpus size
                    corpus_size = len(os.listdir(corpus_dir))

                    # Update our auto-reduction target
                    if corpus_size >= opts.libfuzzer_auto_reduce_min:
                        corpus_auto_reduce_threshold = int(corpus_size * (1 + corpus_auto_reduce_ratio))
                    else:
                        # Corpus is now smaller than --libfuzzer-auto-reduce-min specifies.
                        corpus_auto_reduce_threshold = int(opts.libfuzzer_auto_reduce_min *
                                                           (1 + corpus_auto_reduce_ratio))

                    corpus_reduction_done = True

                    # Continue, our instances will be restarted with the next loop
                    continue

                if opts.stats:
                    stats["corpus_size"] = corpus_size
                    if corpus_auto_reduce_threshold is not None:
                        stats["next_auto_reduce"] = corpus_auto_reduce_threshold

                    write_aggregated_stats_libfuzzer(opts.stats, stats, monitors, [])

                # Only upload new corpus files every 2 hours or after corpus reduction
                if opts.s3_queue_upload and (corpus_reduction_done or last_queue_upload < int(time.time()) - 7200):
                    s3m.upload_libfuzzer_queue_dir(base_dir, corpus_dir, original_corpus)

                    # Pull down queue files from other queues directly into the corpus
                    s3m.download_libfuzzer_queues(corpus_dir)

                    last_queue_upload = int(time.time())
                    corpus_reduction_done = False

                try:
                    result = monitor_queue.get(True, 10)
                except queue.Empty:
                    continue

                monitor = monitors[result]
                monitor.join(20)
                if monitor.is_alive():
                    raise RuntimeError("Monitor %s still alive although it signaled termination." % result)

                # Monitor is dead, mark it for restarts
                monitors[result] = None

                if monitor.exc is not None:
                    # If the monitor had an exception, re-raise it here
                    raise monitor.exc

                if opts.stats:
                    # Make sure the execs that this monitor did survive in stats
                    stats["execs_done"] += monitor.execs_done

                print("Job %s terminated, processing results..." % result, file=sys.stderr)

                trace = monitor.getASanTrace()
                testcase = monitor.getTestcase()
                stderr = monitor.getStderr()

                if not monitor.inited and not trace and not testcase:
                    print("Process did not startup correctly, aborting... (1)", file=sys.stderr)
                    return 2

                # libFuzzer can exit due to OOM with and without a testcase.
                # The case of having an OOM with a testcase is handled further below.
                if not testcase and monitor.hadOOM:
                    stats["ooms"] += 1
                    continue

                # Don't bother sending stuff to the server with neither trace nor testcase
                if not trace and not testcase:
                    continue

                # Ignore slow units and oom files
                if testcase is not None:
                    testcase_name = os.path.basename(testcase)

                    if not monitor.inited:
                        if testcase_name.startswith("oom-") or testcase_name.startswith("timeout-"):
                            hashname = testcase_name.split("-")[1]
                            potential_corpus_file = os.path.join(corpus_dir, hashname)
                            if os.path.exists(potential_corpus_file):
                                print("Removing problematic corpus file %s..." % hashname, file=sys.stderr)
                                os.remove(potential_corpus_file)
                                removed_corpus_files.add(potential_corpus_file)

                            if potential_corpus_file in removed_corpus_files:
                                continue

                        # If neither an OOM or a Timeout caused the startup failure or we couldn't
                        # find and remove the offending file, we should bail out at this point.
                        print("Process did not startup correctly, aborting... (2)", file=sys.stderr)
                        return 2

                    if testcase_name.startswith("slow-unit-"):
                        continue
                    if testcase_name.startswith("oom-"):
                        stats["ooms"] += 1
                        continue
                    if testcase_name.startswith("timeout-"):
                        stats["timeouts"] += 1
                        continue

                stats["crashes"] += 1

                if int(time.time()) - crashes_per_minute_interval > 60:
                    crashes_per_minute_interval = int(time.time())
                    crashes_per_minute = 0
                crashes_per_minute += 1
                stats["crashes_per_minute"] = crashes_per_minute

                if crashes_per_minute >= 10:
                    print("Too many frequent crashes, exiting...", file=sys.stderr)

                    if opts.stats:
                        # If statistics are reported to EC2SpotManager, this helps us to see
                        # when fuzzing has become impossible due to excessive crashes.
                        warning = "Fuzzing terminated due to excessive crashes."
                        write_aggregated_stats_libfuzzer(opts.stats, stats, monitors, [warning])
                    break

                if not monitor.inited:
                    print("Process crashed at startup, aborting...", file=sys.stderr)
                    if opts.stats:
                        # If statistics are reported to EC2SpotManager, this helps us to see
                        # when fuzzing has become impossible due to excessive crashes.
                        warning = "Fuzzing did not startup correctly."
                        write_aggregated_stats_libfuzzer(opts.stats, stats, monitors, [warning])
                    return 2

                # If we run in local mode (no --fuzzmanager specified), then we just continue after each crash
                if not opts.fuzzmanager:
                    continue

                crashInfo = CrashInfo.fromRawCrashData([], stderr, configuration, auxCrashData=trace)

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
        finally:
            try:
                # Before doing anything, try to shutdown our monitors
                for i in range(len(monitors)):
                    if monitors[i] is not None:
                        monitor = monitors[i]
                        monitor.terminate()
                        monitor.join(10)
            finally:
                if sys.exc_info()[0] is not None:
                    # We caught an exception, print it now when all our monitors are down
                    traceback.print_exc()

        return 0

    if opts.aflfuzz:
        if opts.firefox or opts.firefox_start_afl:
            if not haveFFPuppet:
                print("Error: --firefox and --firefox-start-afl require FFPuppet to be installed", file=sys.stderr)
                return 2

            if opts.custom_cmdline_file:
                print("Error: --custom-cmdline-file is incompatible with firefox options", file=sys.stderr)
                return 2

            if not opts.firefox_prefs or not opts.firefox_testpath:
                print("Error: --firefox and --firefox-start-afl require --firefox-prefs"
                      "and --firefox-testpath to be specified", file=sys.stderr)
                return 2

        if opts.firefox_start_afl:
            if not opts.aflbindir:
                print("Error: Must specify --afl-binary-dir for starting AFL with firefox", file=sys.stderr)
                return 2

            (ffp, cmd, env) = setup_firefox(opts.firefox_start_afl, opts.firefox_prefs, opts.firefox_extensions,
                                            opts.firefox_testpath)

            afl_cmd = [os.path.join(opts.aflbindir, "afl-fuzz")]

            opts.rargs.remove("--")

            afl_cmd.extend(opts.rargs)
            afl_cmd.extend(cmd)

            try:
                subprocess.call(afl_cmd, env=env)
            except Exception:
                traceback.print_exc()

            ffp.clean_up()
            return 0

        afl_out_dirs = []
        if opts.afloutdir:
            if not os.path.exists(os.path.join(opts.afloutdir, "crashes")):
                # The specified directory doesn't have a "crashes" sub directory.
                # Either the wrong directory was specified, or this is an AFL multi-process
                # sychronization directory. Try to figure this out here.
                sync_dirs = os.listdir(opts.afloutdir)

                for sync_dir in sync_dirs:
                    if os.path.exists(os.path.join(opts.afloutdir, sync_dir, "crashes")):
                        afl_out_dirs.append(os.path.join(opts.afloutdir, sync_dir))

                if not afl_out_dirs:
                    print("Error: Directory %s does not appear to be a valid AFL output/sync directory"
                          % opts.afloutdir, file=sys.stderr)
                    return 2
            else:
                afl_out_dirs.append(opts.afloutdir)

        # Upload and FuzzManager modes require specifying the AFL directory
        if opts.s3_queue_upload or opts.fuzzmanager:
            if not opts.afloutdir:
                print("Error: Must specify AFL output directory using --afl-output-dir", file=sys.stderr)
                return 2

        if opts.fuzzmanager or opts.s3_queue_upload or opts.aflstats:
            last_queue_upload = 0

            # If we reach this point, we know that AFL will be running on this machine, so do the local warning check
            warn_local()

            while True:
                if opts.fuzzmanager:
                    for afl_out_dir in afl_out_dirs:
                        scan_crashes(afl_out_dir, collector, opts.custom_cmdline_file, opts.env_file, opts.test_file)

                # Only upload queue files every 20 minutes
                if opts.s3_queue_upload and last_queue_upload < int(time.time()) - 1200:
                    for afl_out_dir in afl_out_dirs:
                        s3m.upload_afl_queue_dir(afl_out_dir, new_cov_only=True)
                    last_queue_upload = int(time.time())

                if opts.stats or opts.aflstats:
                    write_aggregated_stats_afl(afl_out_dirs, opts.aflstats, cmdline_path=opts.custom_cmdline_file)

                time.sleep(10)


if __name__ == "__main__":
    sys.exit(main())
