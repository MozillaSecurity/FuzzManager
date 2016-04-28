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

from Collector.Collector import Collector
from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Running.AutoRunner import AutoRunner
import argparse
from boto.s3.connection import S3Connection
from boto.s3.key import Key
import hashlib
from lockfile import FileLock
import os
import platform
import random
import shutil
import stat
import subprocess
import sys
import time


def get_machine_id(base_dir):
    '''
    Get (and if necessary generate) the machine id which is based on
    the current timestamp and the hostname of the machine. The
    generated ID is cached inside the AFL base directory, so all
    future calls to this method return the same ID.
    
    @type base_dir: String
    @param base_dir: AFL base directory
    
    @rtype: String
    @return: The generated/cached machine ID
    '''
    id_file = os.path.join(base_dir, "s3_id")
    
    # We initially create a unique ID based on the hostname and the
    # current timestamp, then we store this ID in a file inside the
    # fuzzing working directory so we can retrieve it later.
    if not os.path.exists(id_file):
        h = hashlib.new('sha1')
        h.update(platform.node())
        h.update(str(time.time()))
        id = h.hexdigest()
        with open(id_file, 'w') as id_fd:
            id_fd.write(id)
        return id
    else:
        with open(id_file, 'r') as id_fd:
            return id_fd.read()
        
def write_aggregated_stats(base_dirs, outfile):
    '''
    Generate aggregated statistics from the given base directories
    and write them to the specified output file.
    
    @type base_dirs: list
    @param base_dirs: List of AFL base directories

    @type outfile: str
    @param outfile: Output file for aggregated statistics
    '''
    
    # Which fields to add
    wanted_fields_total = [ 
                           'execs_done', 
                           'execs_per_sec', 
                           'pending_favs', 
                           'pending_total', 
                           'variable_paths', 
                           'unique_crashes', 
                           'unique_hangs'  
                           ]
    
    # Which fields to aggregate by mean
    wanted_fields_mean = [ 'exec_timeout' ]
    
    # Which fields should be displayed per fuzzer instance
    wanted_fields_all = [ 'cycles_done',  'bitmap_cvg' ]
    
    # Which fields should be aggregated by max
    wanted_fields_max = [ 'last_path' ]
    
    aggregated_stats = {}
    
    for field in wanted_fields_total:
        aggregated_stats[field] = 0
    
    for field in wanted_fields_mean:
        aggregated_stats[field] = (0,0)
        
    for field in wanted_fields_all:
        aggregated_stats[field] = []
    
    def convert_num(num):
        if '.' in num:
            return float(num)
        return int(num)
    
    for base_dir in base_dirs:
        stats_path = os.path.join(base_dir, "fuzzer_stats")
        
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
                    if (not field_name in aggregated_stats) or aggregated_stats[field_name] < num_val:
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

    # Write out data
    fields = []
    fields.extend(wanted_fields_total)
    fields.extend(wanted_fields_mean)
    fields.extend(wanted_fields_all)
    fields.extend(wanted_fields_max)
    
    max_keylen = max([len(x) for x in fields])
    
    lock = FileLock(outfile)
    lock.acquire()
    with open(outfile, 'w') as f:
        for field in fields:
            if not field in aggregated_stats:
                continue
            
            val = aggregated_stats[field]
            
            if isinstance(val, list):
                val = " ".join(val)
            
            f.write("%s%s: %s\n" % (field, " " * (max_keylen + 1 - len(field)), val))
    lock.release() 
    
    return

def scan_crashes(base_dir, cmdline_path=None, env_path=None, tool_name=None):
    '''
    Scan the base directory for crash tests and submit them to FuzzManager.
    
    @type base_dir: String
    @param base_dir: AFL base directory
    
    @type cmdline_path: String
    @param cmdline_path: Optional command line file to use instead of the
                         one found inside the base directory.
                         
    @type env_path: String
    @param env_path: Optional file containing environment variables.   
    
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
        cmdline = []
        test_idx = None
        
        base_env = {}
        test_in_env = None
        if env_path:
            with open(env_path, 'r') as env_file:
                for line in env_file:
                    (name,val) = line.rstrip('\n').split("=", 1)
                    base_env[name] = val
                    
                    if '@@' in val:
                        test_in_env = name
        
        if not cmdline_path:
            cmdline_path = os.path.join(base_dir, "cmdline")
        
        with open(cmdline_path, 'r') as cmdline_file:
            idx = 0
            for line in cmdline_file:
                if '@@' in line:
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
        
        collector = Collector(tool=tool_name)
        
        for crash_file in crash_files:
            stdin = None
            env = None
            
            if base_env:
                env = dict(base_env)

            if test_idx != None:
                cmdline[test_idx] = orig_test_arg.replace('@@', crash_file)
            elif test_in_env != None:
                env[test_in_env] = env[test_in_env].replace('@@', crash_file)
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

def upload_queue_dir(base_dir, bucket_name, project_name, new_cov_only=True):
    '''
    Synchronize the queue directory of the specified AFL base directory
    to the specified S3 bucket. This method only uploads files that don't
    exist yet on the receiving side. 
    
    @type base_dir: String
    @param base_dir: AFL base directory
    
    @type bucket_name: String
    @param bucket_name: Name of the S3 bucket to use
    
    @type project_name: String
    @param project_name: Name of the project folder inside the S3 bucket
    
    @type new_cov_only: Boolean
    @param new_cov_only: Only upload files that have new coverage
    '''
    queue_dir = os.path.join(base_dir, "queue")
    queue_files = []

    for queue_file in os.listdir(queue_dir):
        # Ignore all files that aren't crash results
        if not queue_file.startswith("id:"):
            continue
        
        # Only upload files that have new coverage if we aren't told
        # otherwise by the caller.
        if new_cov_only and not "+cov" in queue_file:
            continue
        
        # Ignore files that have been obtained from other local queues
        # to avoid duplicate uploading
        if ",sync:" in queue_file:
            continue
        
        queue_files.append(queue_file)

    cmdline_file = os.path.join(base_dir, "cmdline")
    
    conn = S3Connection()
    bucket = conn.get_bucket(bucket_name)
    
    remote_path = "%s/queues/%s/" % (project_name, get_machine_id(base_dir))
    
    remote_files = [key.name.replace(remote_path, "", 1) for key in list(bucket.list(remote_path))]
    
    upload_list = []
    
    for queue_file in queue_files:
        if not queue_file in remote_files:
            upload_list.append(os.path.join(queue_dir, queue_file))
    
    if not "cmdline" in remote_files:
        upload_list.append(cmdline_file)
    
    for upload_file in upload_list:
        remote_key = Key(bucket)
        remote_key.name = remote_path + os.path.basename(upload_file)
        print("Uploading file %s -> %s" % (upload_file, remote_key.name))
        remote_key.set_contents_from_filename(upload_file)
        
def download_queue_dirs(work_dir, bucket_name, project_name):
    '''
    Downloads all queue files into the queues sub directory of the specified
    local work directory. The files are renamed to match their SHA1 hashes
    to avoid file collisions.
    
    @type base_dir: String
    @param base_dir: Local work directory
    
    @type bucket_name: String
    @param bucket_name: Name of the S3 bucket to use
    
    @type project_name: String
    @param project_name: Name of the project folder inside the S3 bucket
    '''
    download_dir = os.path.join(work_dir, "queues")
    
    if not os.path.exists(download_dir):
        os.mkdir(download_dir)
    
    conn = S3Connection()
    bucket = conn.get_bucket(bucket_name)
    
    remote_path = "%s/queues/" % project_name
        
    remote_keys = list(bucket.list(remote_path))
    
    for remote_key in remote_keys:
        # Ignore any folders
        if remote_key.name.endswith("/"):
            continue
        
        # Perform a HEAD request to get metadata included
        remote_key = bucket.get_key(remote_key.name)
        
        if remote_key.get_metadata('downloaded'):
            # Don't download the same file twice
            continue
        
        # If we see a cmdline file, fetch it into the main work directory
        if os.path.basename(remote_key.name) == 'cmdline':
            remote_key.get_contents_to_filename(os.path.join(work_dir, 'cmdline'))
            remote_key = remote_key.copy(remote_key.bucket.name, remote_key.name, {'downloaded' : int(time.time())}, preserve_acl=True)
            continue
        
        tmp_file = os.path.join(download_dir, "tmp")
        
        remote_key.get_contents_to_filename(tmp_file)
        
        with open(tmp_file, 'r') as tmp_fd:
            h = hashlib.new('sha1')
            h.update(str(tmp_fd.read()))
            hash_name = h.hexdigest()
        
        os.rename(tmp_file, os.path.join(download_dir, hash_name))
        
        # Ugly, but we have to do a remote copy of the file to change the metadata
        remote_key = remote_key.copy(remote_key.bucket.name, remote_key.name, {'downloaded' : int(time.time())}, preserve_acl=True)

def clean_queue_dirs(work_dir, bucket_name, project_name, min_age = 86400):
    '''
    Delete all remote queues that have a downloaded attribute that is older
    than the specified time interval, defaulting to 24 hours.
    
    @type base_dir: String
    @param base_dir: Local work directory
    
    @type bucket_name: String
    @param bucket_name: Name of the S3 bucket to use
    
    @type project_name: String
    @param project_name: Name of the project folder inside the S3 bucket
    
    @type min_age: int
    @param min_age: Minimum age of the key before it is deleted
    '''
    
    conn = S3Connection()
    bucket = conn.get_bucket(bucket_name)
    
    remote_path = "%s/queues/" % project_name
        
    remote_keys = list(bucket.list(remote_path))
    remote_keys_for_deletion = []
    
    for remote_key in remote_keys:
        # Ignore any folders
        if remote_key.name.endswith("/"):
            continue
        
        # Perform a HEAD request to get metadata included
        remote_key = bucket.get_key(remote_key.name)
        
        downloaded = remote_key.get_metadata('downloaded')
        
        if not downloaded or int(downloaded) > (int(time.time()) - min_age):
            continue
        
        remote_keys_for_deletion.append(remote_key.name)
    
    for remote_key_for_deletion in remote_keys_for_deletion:
        print("Deleting old key %s" % remote_key_for_deletion)
         
    bucket.delete_keys(remote_keys_for_deletion, quiet=True)

def get_queue_status(bucket_name, project_name):
    '''
    Return status data for all queues in the specified S3 bucket/project
    
    @type bucket_name: String
    @param bucket_name: Name of the S3 bucket to use
    
    @type project_name: String
    @param project_name: Name of the project folder inside the S3 bucket
    
    @rtype: dict
    @return: Dictionary containing queue size per queue
    '''
    
    conn = S3Connection()
    bucket = conn.get_bucket(bucket_name)
    
    remote_path = "%s/queues/" % project_name
    remote_keys = list(bucket.list(remote_path))
    
    status_data = {}
    
    for remote_key in remote_keys:
        # Ignore any folders
        if remote_key.name.endswith("/"):
            continue
        
        (queue_name, filename) = remote_key.name.rsplit("/", 1)
        
        if not queue_name in status_data:
            status_data[queue_name] = 0
        status_data[queue_name] += 1
    
    return status_data

def download_build(build_dir, bucket_name, project_name):
    '''
    Downloads build.zip from the specified S3 bucket and unpacks it
    into the specified build directory.
    
    @type base_dir: String
    @param base_dir: Build directory
    
    @type bucket_name: String
    @param bucket_name: Name of the S3 bucket to use
    
    @type project_name: String
    @param project_name: Name of the project folder inside the S3 bucket
    '''
    
    # Clear any previous builds
    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
    
    os.mkdir(build_dir)
    
    zip_dest = os.path.join(build_dir, "build.zip")
    
    conn = S3Connection()
    bucket = conn.get_bucket(bucket_name)
    
    remote_key = Key(bucket)
    remote_key.name = "%s/build.zip" % project_name
    remote_key.get_contents_to_filename(zip_dest)
    
    subprocess.check_call(["unzip", zip_dest, "-d", build_dir])

def download_corpus(corpus_dir, bucket_name, project_name, random_subset_size=None):
    '''
    Downloads the test corpus from the specified S3 bucket and project
    into the specified directory, without overwriting any files.
    
    @type corpus_dir: String
    @param corpus_dir: Directory where to store test corpus files
    
    @type bucket_name: String
    @param bucket_name: Name of the S3 bucket to use
    
    @type project_name: String
    @param project_name: Name of the project folder inside the S3 bucket
    
    @type random_subset_size: int
    @param random_subset_size: If specified, only download a random subset of
                               the corpus, with the specified size.
    '''
    if not os.path.exists(corpus_dir): 
        os.mkdir(corpus_dir)
    
    conn = S3Connection()
    bucket = conn.get_bucket(bucket_name)
    
    remote_path = "%s/corpus/" % project_name
        
    remote_keys = list(bucket.list(remote_path))
    
    if random_subset_size and len(remote_keys) > random_subset_size:
        remote_keys = random.sample(remote_keys, random_subset_size)
    
    for remote_key in remote_keys:
        dest_file = os.path.join(corpus_dir, os.path.basename(remote_key.name))
        
        if not os.path.exists(dest_file):
            remote_key.get_contents_to_filename(dest_file)

def upload_corpus(corpus_dir, bucket_name, project_name, corpus_delete=False):
    '''
    Synchronize the specified test corpus directory to the specified S3 bucket. 
    This method only uploads files that don't exist yet on the receiving side. 
    
    @type corpus_dir: String
    @param corpus_dir: Directory where the test corpus files are stored
    
    @type bucket_name: String
    @param bucket_name: Name of the S3 bucket to use
    
    @type project_name: String
    @param project_name: Name of the project folder inside the S3 bucket

    @type corpus_delete: bool
    @param corpus_delete: Delete all remote files that don't exist on our side
    '''
    test_files = [file for file in os.listdir(corpus_dir) if os.path.isfile(os.path.join(corpus_dir, file))]
    
    if not test_files:
        print("Error: Corpus is empty, refusing upload.", file=sys.stderr)
        return
    
    conn = S3Connection()
    bucket = conn.get_bucket(bucket_name)
    
    remote_path = "%s/corpus/" % project_name
    
    remote_files = [key.name.replace(remote_path, "", 1) for key in list(bucket.list(remote_path))]
    
    upload_list = []
    delete_list = []
    
    for test_file in test_files:
        if not test_file in remote_files:
            upload_list.append(os.path.join(corpus_dir, test_file))
    
    if corpus_delete:
        for remote_file in remote_files:
            if not remote_file in test_files:
                delete_list.append(remote_path + remote_file)
    
    for upload_file in upload_list:
        remote_key = Key(bucket)
        remote_key.name = remote_path + os.path.basename(upload_file)
        print("Uploading file %s -> %s" % (upload_file, remote_key.name))
        remote_key.set_contents_from_filename(upload_file)
    
    if corpus_delete:    
        bucket.delete_keys(delete_list, quiet=True)
    
def upload_build(build_file, bucket_name, project_name):
    '''
    Upload the given build zip file to the specified S3 bucket/project
    directory.
    
    @type build_file: String
    @param build_file: (ZIP) file containing the build that should be uploaded
    
    @type bucket_name: String
    @param bucket_name: Name of the S3 bucket to use
    
    @type project_name: String
    @param project_name: Name of the project folder inside the S3 bucket
    '''

    if not os.path.exists(build_file) or not os.path.isfile(build_file):
        print("Error: Build must be a (zip) file.", file=sys.stderr)
        return
    
    conn = S3Connection()
    bucket = conn.get_bucket(bucket_name)
    
    remote_file = "%s/build.zip" % project_name
    
    remote_key = Key(bucket)
    remote_key.name = remote_file
    print("Uploading file %s -> %s" % (build_file, remote_key.name))
    remote_key.set_contents_from_filename(build_file)

def main(argv=None):
    '''Command line options.'''

    program_name = os.path.basename(sys.argv[0])

    if argv is None:
        argv = sys.argv[1:]

    # setup argparser
    parser = argparse.ArgumentParser()

    parser.add_argument("--s3-queue-upload", dest="s3_queue_upload", action='store_true', help="Use S3 to synchronize queues")
    parser.add_argument("--s3-queue-cleanup", dest="s3_queue_cleanup", action='store_true', help="Cleanup S3 queue entries older than specified refresh interval")
    parser.add_argument("--s3-queue-status", dest="s3_queue_status", action='store_true', help="Display S3 queue status")
    parser.add_argument("--s3-build-download", dest="s3_build_download", help="Use S3 to download the build for the specified project", metavar="DIR")
    parser.add_argument("--s3-build-upload", dest="s3_build_upload", help="Use S3 to upload a new build for the specified project", metavar="FILE")
    parser.add_argument("--s3-corpus-download", dest="s3_corpus_download", help="Use S3 to download the test corpus for the specified project", metavar="DIR")
    parser.add_argument("--s3-corpus-download-size", dest="s3_corpus_download_size", help="When downloading the corpus, select only SIZE files randomly", metavar="SIZE")
    parser.add_argument("--s3-corpus-upload", dest="s3_corpus_upload", help="Use S3 to upload a test corpus for the specified project", metavar="DIR")
    parser.add_argument("--s3-corpus-replace", dest="s3_corpus_replace", action='store_true', help="In conjunction with --s3-corpus-upload, deletes all other remote test files")
    parser.add_argument("--s3-corpus-refresh", dest="s3_corpus_refresh", help="Download queues and corpus from S3, combine and minimize, then re-upload.", metavar="DIR")
    parser.add_argument("--fuzzmanager", dest="fuzzmanager", action='store_true', help="Use FuzzManager to submit crash results")
    parser.add_argument("--fuzzmanager-toolname", dest="fuzzmanager_toolname", help="Override FuzzManager tool name (for submitting crash results)")
    parser.add_argument("--custom-cmdline-file", dest="custom_cmdline_file", help="Path to custom cmdline file", metavar="FILE")
    parser.add_argument("--env-file", dest="env_file", help="Path to a file with additional environment variables", metavar="FILE")
    parser.add_argument("--s3-refresh-interval", dest="s3_refresh_interval", type=int, default=86400, help="How often the s3 corpus is refreshed (affects queue cleaning)", metavar="SECS")
    parser.add_argument("--afl-output-dir", dest="afloutdir", help="Path to the AFL output directory to manage", metavar="DIR")
    parser.add_argument("--afl-binary-dir", dest="aflbindir", help="Path to the AFL binary directory to use", metavar="DIR")
    parser.add_argument("--afl-stats", dest="aflstats", help="Collect aggregated statistics while scanning output directories", metavar="FILE")
    
    parser.add_argument("--s3-bucket", dest="s3_bucket", help="Name of the S3 bucket to use", metavar="NAME")
    parser.add_argument("--project", dest="project", help="Name of the subfolder/project inside the S3 bucket", metavar="NAME")

    parser.add_argument('rargs', nargs=argparse.REMAINDER)

    if len(argv) == 0:
        parser.print_help()
        return 2

    # process options
    opts = parser.parse_args(argv)
    
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
                print("Error: Directory %s does not appear to be a valid AFL output/sync directory" % opts.afloutdir, file=sys.stderr)
                return 2
        else:
            afl_out_dirs.append(opts.afloutdir)
    
    # Upload and FuzzManager modes require specifying the AFL directory
    if opts.s3_queue_upload or opts.fuzzmanager:
        if not opts.afloutdir:
            print("Error: Must specify AFL output directory using --afl-output-dir", file=sys.stderr)
            return 2
        
    if (opts.s3_queue_upload 
        or opts.s3_corpus_refresh 
        or opts.s3_build_download 
        or opts.s3_build_upload 
        or opts.s3_corpus_download 
        or opts.s3_corpus_upload
        or opts.s3_queue_status):
        if not opts.s3_bucket or not opts.project:
            print("Error: Must specify both --s3-bucket and --project for S3 actions", file=sys.stderr)
            return 2
        
    if opts.s3_queue_status:
        status_data = get_queue_status(opts.s3_bucket, opts.project)
        total_queue_files = 0
        
        for queue_name in status_data:
            print("Queue %s: %s" % (queue_name, status_data[queue_name]))
            total_queue_files += status_data[queue_name]
        print("Total queue files: %s" % total_queue_files)
        
        return 0        
    
    if opts.s3_queue_cleanup:
        clean_queue_dirs(opts.s3_corpus_refresh, opts.s3_bucket, opts.project, opts.s3_refresh_interval)
        return 0
    
    if opts.s3_build_download:
        download_build(opts.s3_build_download, opts.s3_bucket, opts.project)
        return 0

    if opts.s3_build_upload:
        upload_build(opts.s3_build_upload, opts.s3_bucket, opts.project)
        return 0
    
    if opts.s3_corpus_download:
        if opts.s3_corpus_download_size != None:
            opts.s3_corpus_download_size = int(opts.s3_corpus_download_size)
                
        download_corpus(opts.s3_corpus_download, opts.s3_bucket, opts.project, opts.s3_corpus_download_size)
        return 0
    
    if opts.s3_corpus_upload:
        upload_corpus(opts.s3_corpus_upload, opts.s3_bucket, opts.project, opts.s3_corpus_replace)
        return 0

    if opts.s3_corpus_refresh:
        if not opts.aflbindir:
            print("Error: Must specify --afl-binary-dir for refreshing the test corpus", file=sys.stderr)
            return 2
        
        if not os.path.exists(opts.s3_corpus_refresh):
            os.makedirs(opts.s3_corpus_refresh)
            
        queues_dir = os.path.join(opts.s3_corpus_refresh, "queues")
        
        print("Cleaning old AFL queues from s3://%s/%s/queues/" % (opts.s3_bucket, opts.project))
        clean_queue_dirs(opts.s3_corpus_refresh, opts.s3_bucket, opts.project, opts.s3_refresh_interval)
        
        print("Downloading AFL queues from s3://%s/%s/queues/ to %s" % (opts.s3_bucket, opts.project, queues_dir)) 
        download_queue_dirs(opts.s3_corpus_refresh, opts.s3_bucket, opts.project)
        
        cmdline_file = os.path.join(opts.s3_corpus_refresh, "cmdline")
        if not os.path.exists(cmdline_file):
            print("Error: Failed to download a cmdline file from queue directories.", file=sys.stderr)
            return 2
        
        download_build(os.path.join(opts.s3_corpus_refresh, "build"), opts.s3_bucket, opts.project)
        
        cmdline = []
        with open(os.path.join(opts.s3_corpus_refresh, "cmdline"), 'r') as cmdline_file:
            for line in cmdline_file:
                cmdline.append(line.rstrip('\n'))
                
        # Assume cmdline[0] is the name of the binary
        binary_name = os.path.basename(cmdline[0])
        
        # Try locating our binary in the build we just unpacked
        binary_search_result = [os.path.join(dirpath, filename) 
            for dirpath, dirnames, filenames in os.walk(os.path.join(opts.s3_corpus_refresh, "build")) 
                for filename in filenames 
                    if (filename == binary_name and (stat.S_IXUSR & os.stat(os.path.join(dirpath, filename))[stat.ST_MODE]))]
        
        if not binary_search_result:
            print("Error: Failed to locate binary %s in unpacked build." % binary_name, file=sys.stderr)
            return 2
        
        if len(binary_search_result) > 1:
            print("Error: Binary name %s is ambiguous in unpacked build." % binary_name, file=sys.stderr)
            return 2
        
        cmdline[0] = binary_search_result[0]
        
        # Download our current corpus into the queues directory as well
        download_corpus(queues_dir, opts.s3_bucket, opts.project)
        
        # Ensure the directory for our new tests is empty
        updated_tests_dir = os.path.join(opts.s3_corpus_refresh, "tests")
        if os.path.exists(updated_tests_dir):
            shutil.rmtree(updated_tests_dir)
        os.mkdir(updated_tests_dir)
        
        # Run afl-cmin
        afl_cmin = os.path.join(opts.aflbindir, "afl-cmin")
        if not os.path.exists(afl_cmin):
            print("Error: Unable to locate afl-cmin binary.", file=sys.stderr)
            return 2
        
        afl_cmdline = [afl_cmin, '-e', '-i', queues_dir, '-o', updated_tests_dir, '-t', '1000', '-m', 'none']
        afl_cmdline.extend(cmdline)
        
        with open(os.devnull, 'w') as devnull:
            env = os.environ.copy()
            env['LD_LIBRARY_PATH'] = os.path.dirname(cmdline[0])
            subprocess.check_call(afl_cmdline, stdout=devnull, env=env)
        
        upload_corpus(updated_tests_dir, opts.s3_bucket, opts.project, True)
        
        # Prune the queues directory once we successfully uploaded the new
        # test corpus, but leave everything that's part of our new corpus
        # so we don't have to download those files again.
        test_files = [file for file in os.listdir(updated_tests_dir) if os.path.isfile(os.path.join(updated_tests_dir, file))]
        obsolete_queue_files = [file for file in os.listdir(queues_dir) if os.path.isfile(os.path.join(queues_dir, file)) and file not in test_files]
        
        for file in obsolete_queue_files:
            os.remove(os.path.join(queues_dir, file))
    
    if opts.fuzzmanager or opts.s3_queue_upload or opts.aflstats:
        last_queue_upload = 0
        while True:
            if opts.fuzzmanager:
                for afl_out_dir in afl_out_dirs:
                    scan_crashes(afl_out_dir, opts.custom_cmdline_file, opts.env_file, opts.fuzzmanager_toolname)
            
            # Only upload queue files every 20 minutes
            if opts.s3_queue_upload and last_queue_upload < int(time.time()) - 1200:
                for afl_out_dir in afl_out_dirs:
                    upload_queue_dir(afl_out_dir, opts.s3_bucket, opts.project, new_cov_only=True)
                last_queue_upload = int(time.time())
            
            if opts.aflstats:
                write_aggregated_stats(afl_out_dirs, opts.aflstats)
                
            time.sleep(10)

if __name__ == "__main__":
    sys.exit(main())
