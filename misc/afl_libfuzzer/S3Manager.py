# encoding: utf-8
'''
S3Manager -- Class to manage builds, corpus and queues for AFL and libFuzzer on AWS S3

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

from boto.s3.connection import S3Connection
from boto.s3.key import Key
from boto.utils import parse_ts as boto_parse_ts

from tempfile import mkstemp
from zipfile import ZipFile, ZIP_DEFLATED

import hashlib
import os
import platform
import random
import shutil
import subprocess
import sys
import time


class S3Manager():
    def __init__(self, bucket_name, project_name, build_project_name=None, zip_name="build.zip"):
        '''
        @type bucket_name: String
        @param bucket_name: Name of the S3 bucket to use

        @type project_name: String
        @param project_name: Name of the project folder inside the S3 bucket

        @type cmdline_file: String
        @param cmdline_file: Path to the cmdline file to upload.
        '''
        self.bucket_name = bucket_name
        self.project_name = project_name
        self.build_project_name = build_project_name
        self.zip_name = zip_name

        self.connection = S3Connection()
        self.bucket = self.connection.get_bucket(self.bucket_name)

        # Define some path constants that define the folder structure on S3
        self.remote_path_queues = "%s/queues/" % self.project_name
        self.remote_path_corpus = "%s/corpus/" % self.project_name
        self.remote_path_corpus_bundle = "%s/corpus.zip" % self.project_name

        if self.build_project_name:
            self.remote_path_build = "%s/%s" % (self.build_project_name, self.zip_name)
        else:
            self.remote_path_build = "%s/%s" % (self.project_name, self.zip_name)

        # Memorize which files we have uploaded/downloaded before, so we never attempt to
        # re-upload them to a different queue or re-download them after a local merge.
        self.uploaded_files = set()
        self.downloaded_files = set()

    def upload_libfuzzer_queue_dir(self, base_dir, corpus_dir, original_corpus):
        '''
        Synchronize the corpus directory of the specified libFuzzer corpus directory
        to the specified S3 bucket. This method only uploads files that don't
        exist yet on the receiving side and excludes all files in the original corpus.

        @type base_dir: String
        @param base_dir: libFuzzer base directory

        @type corpus_dir: String
        @param corpus_dir: libFuzzer corpus directory

        @type original_corpus: Set
        @param original_corpus: Set of original corpus files to exclude from synchronization
        '''
        upload_files = [x for x in os.listdir(corpus_dir) if x not in original_corpus and x not in self.uploaded_files]

        # Memorize files selected for upload
        self.uploaded_files.update(upload_files)

        cmdline_file = os.path.join(base_dir, "cmdline")

        return self.__upload_queue_files(corpus_dir, upload_files, base_dir, cmdline_file)

    def download_libfuzzer_queues(self, corpus_dir):
        '''
        Synchronize files from open libFuzzer queues directly back into the local corpus directory.

        @type corpus_dir: String
        @param corpus_dir: libFuzzer corpus directory
        '''
        remote_keys = list(self.bucket.list(self.remote_path_queues))
        remote_queues_closed_names = [x.name.rsplit("/", 1)[0] for x in remote_keys if x.name.endswith("/closed")]

        for remote_key in remote_keys:
            # Ignore any folders
            if remote_key.name.endswith("/"):
                continue

            # Ignore the cmdline and closed files
            if remote_key.name.endswith("/cmdline") or remote_key.name.endswith("/closed"):
                continue

            (queue_name, filename) = remote_key.name.rsplit("/", 1)

            if queue_name in remote_queues_closed_names:
                # If the file is in a queue marked as closed, ignore it
                continue

            basename = os.path.basename(remote_key.name)

            if basename in self.downloaded_files or basename in self.uploaded_files:
                # If we ever downloaded this file before, ignore it
                continue

            dest_file = os.path.join(corpus_dir, basename)
            if os.path.exists(dest_file):
                # If the file already exists locally, ignore it
                continue

            print("Syncing from queue %s: %s" % (queue_name, filename))
            remote_key.get_contents_to_filename(dest_file)

            self.downloaded_files.add(basename)

    def upload_afl_queue_dir(self, base_dir, new_cov_only=True):
        '''
        Synchronize the queue directory of the specified AFL base directory
        to the specified S3 bucket. This method only uploads files that don't
        exist yet on the receiving side.

        @type base_dir: String
        @param base_dir: AFL base directory

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
            if new_cov_only and "+cov" not in queue_file:
                continue

            # Ignore files that have been obtained from other local queues
            # to avoid duplicate uploading
            if ",sync:" in queue_file:
                continue

            queue_files.append(queue_file)

        cmdline_file = os.path.join(base_dir, "cmdline")
        return self.__upload_queue_files(queue_dir, queue_files, base_dir, cmdline_file)

    def download_queue_dirs(self, work_dir):
        '''
        Downloads all queue files into the queues sub directory of the specified
        local work directory. The files are renamed to match their SHA1 hashes
        to avoid file collisions.

        This method marks all remote queues that have been downloaded as closed.

        @type work_dir: String
        @param work_dir: Local work directory
        '''
        download_dir = os.path.join(work_dir, "queues")

        if not os.path.exists(download_dir):
            os.mkdir(download_dir)

        remote_keys = list(self.bucket.list(self.remote_path_queues))

        remote_queue_names = set()
        remote_queues_already_closed = set()

        # Close all queues that aren't closed already.
        # This will stop the clients from uploading new data into these queues.
        #
        # Unfortunately we have to iterate over all files in the queue path to figure out which queues exist.
        # Then we have to determine which of them might already been closed (this shouldn't happen normally),
        # but we should check this anyway and not consider it an error.
        for remote_key in remote_keys:
            (queue_name, filename) = remote_key.name.rsplit("/", 1)
            remote_queue_names.add(queue_name)
            if filename == "closed":
                remote_queues_already_closed.add(queue_name)

        for remote_queue_name in remote_queue_names:
            if remote_queue_name not in remote_queues_already_closed:
                closed_key = self.bucket.new_key(remote_queue_name + "/closed")
                closed_key.set_contents_from_string('')

        for remote_key in remote_keys:
            # Ignore any folders and the closed file
            if remote_key.name.endswith("/") or remote_key.name.endswith("/closed"):
                continue

            (queue_name, filename) = remote_key.name.rsplit("/", 1)

            # This queue was closed before, assume we downloaded it before to save download requests.
            if queue_name in remote_queues_already_closed:
                continue

            # If we see a cmdline file, fetch it into the main work directory
            if os.path.basename(remote_key.name) == 'cmdline':
                remote_key.get_contents_to_filename(os.path.join(work_dir, 'cmdline'))
                continue

            tmp_file = os.path.join(download_dir, "tmp")

            remote_key.get_contents_to_filename(tmp_file)

            with open(tmp_file, 'rb') as tmp_fd:
                hash_name = hashlib.sha1(tmp_fd.read()).hexdigest()

            os.rename(tmp_file, os.path.join(download_dir, hash_name))

    def clean_queue_dirs(self):
        '''
        Delete all closed remote queues.
        '''
        remote_keys = list(self.bucket.list(self.remote_path_queues))
        remote_keys_for_deletion = []

        remote_queues_closed_names = [x.name.rsplit("/", 1)[0] for x in remote_keys if x.name.endswith("/closed")]

        for remote_key in remote_keys:
            # For folders, check if they are empty and if so, remove them
            if remote_key.name.endswith("/"):
                #TODO: This might not work in current boto, check later
                if remote_key.size == 0:
                    remote_keys_for_deletion.append(remote_key.name)
                continue

            (queue_name, filename) = remote_key.name.rsplit("/", 1)
            if queue_name in remote_queues_closed_names:
                remote_keys_for_deletion.append(remote_key.name)

        for remote_key_for_deletion in remote_keys_for_deletion:
            print("Deleting old key %s" % remote_key_for_deletion)

        self.bucket.delete_keys(remote_keys_for_deletion, quiet=True)

    def get_queue_status(self):
        '''
        Return status data for all queues in the specified S3 bucket/project

        @rtype: dict
        @return: Dictionary containing queue size per queue
        '''
        remote_keys = list(self.bucket.list(self.remote_path_queues))
        remote_queues_closed_names = [x.name.rsplit("/", 1)[0] for x in remote_keys if x.name.endswith("/closed")]

        status_data = {}

        for remote_key in remote_keys:
            # Ignore any folders
            if remote_key.name.endswith("/"):
                continue

            # Ignore the cmdline and closed files
            if remote_key.name.endswith("/cmdline") or remote_key.name.endswith("/closed"):
                continue

            (queue_name, filename) = remote_key.name.rsplit("/", 1)

            if queue_name in remote_queues_closed_names:
                queue_name += "*"

            if queue_name not in status_data:
                status_data[queue_name] = 0
            status_data[queue_name] += 1

        return status_data

    def get_corpus_status(self):
        '''
        Return status data for the corpus of the specified S3 bucket/project

        @type bucket_name: String
        @param bucket_name: Name of the S3 bucket to use

        @type project_name: String
        @param project_name: Name of the project folder inside the S3 bucket

        @rtype: dict
        @return: Dictionary containing corpus size per date modified
        '''
        remote_keys = list(self.bucket.list(self.remote_path_corpus))

        status_data = {}

        for remote_key in remote_keys:
            # Ignore any folders
            if remote_key.name.endswith("/"):
                continue

            dt = boto_parse_ts(remote_key.last_modified)

            date_str = "%s-%02d-%02d" % (dt.year, dt.month, dt.day)

            if date_str not in status_data:
                status_data[date_str] = 0
            status_data[date_str] += 1

        return status_data

    def download_build(self, build_dir):
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

        zip_dest = os.path.join(build_dir, self.zip_name)

        remote_key = Key(self.bucket)
        remote_key.name = self.remote_path_build
        remote_key.get_contents_to_filename(zip_dest)

        subprocess.check_call(["unzip", zip_dest, "-d", build_dir])

    def upload_build(self, build_file):
        '''
        Upload the given build zip file to the specified S3 bucket/project
        directory.

        @type build_file: String
        @param build_file: (ZIP) file containing the build that should be uploaded
        '''

        if not os.path.exists(build_file) or not os.path.isfile(build_file):
            print("Error: Build must be a (zip) file.", file=sys.stderr)
            return

        remote_key = Key(self.bucket)
        remote_key.name = self.remote_path_build
        print("Uploading file %s -> %s" % (build_file, remote_key.name))
        remote_key.set_contents_from_filename(build_file)

    def download_corpus(self, corpus_dir, random_subset_size=None):
        '''
        Downloads the test corpus from the specified S3 bucket and project
        into the specified directory, without overwriting any files.

        @type corpus_dir: String
        @param corpus_dir: Directory where to store test corpus files

        @type random_subset_size: int
        @param random_subset_size: If specified, only download a random subset of
                                   the corpus, with the specified size.
        '''
        if not os.path.exists(corpus_dir):
            os.mkdir(corpus_dir)

        if not random_subset_size:
            # If we are not instructed to download only a sample of the corpus,
            # we can try and look for a corpus bundle (zip file) for faster download.
            remote_key = Key(self.bucket)
            remote_key.name = self.remote_path_corpus_bundle
            if remote_key.exists():
                (zip_fd, zip_dest) = mkstemp(prefix="libfuzzer-s3-corpus")
                print("Found corpus bundle, downloading...")

                try:
                    remote_key.get_contents_to_filename(zip_dest)

                    with ZipFile(zip_dest, "r") as zip_file:
                        if zip_file.testzip():
                            # Warn, but don't throw, we can try to download the corpus directly
                            print("Bad CRC for downloaded zipfile %s" % zip_dest, file=sys.stderr)
                        else:
                            zip_file.extractall(corpus_dir)
                            return
                finally:
                    os.remove(zip_dest)

        remote_keys = list(self.bucket.list(self.remote_path_corpus))

        if random_subset_size and len(remote_keys) > random_subset_size:
            remote_keys = random.sample(remote_keys, random_subset_size)

        for remote_key in remote_keys:
            dest_file = os.path.join(corpus_dir, os.path.basename(remote_key.name))

            if not os.path.exists(dest_file):
                remote_key.get_contents_to_filename(dest_file)

    def upload_corpus(self, corpus_dir, corpus_delete=False):
        '''
        Synchronize the specified test corpus directory to the specified S3 bucket.
        This method only uploads files that don't exist yet on the receiving side.

        @type corpus_dir: String
        @param corpus_dir: Directory where the test corpus files are stored

        @type corpus_delete: bool
        @param corpus_delete: Delete all remote files that don't exist on our side
        '''
        test_files = [file for file in os.listdir(corpus_dir) if os.path.isfile(os.path.join(corpus_dir, file))]

        if not test_files:
            print("Error: Corpus is empty, refusing upload.", file=sys.stderr)
            return

        # Make a zip bundle and upload it
        (zip_fd, zip_dest) = mkstemp(prefix="libfuzzer-s3-corpus")
        zip_file = ZipFile(zip_dest, 'w', ZIP_DEFLATED)
        for test_file in test_files:
            zip_file.write(os.path.join(corpus_dir, test_file), arcname=test_file)
        zip_file.close()
        remote_key = Key(self.bucket)
        remote_key.name = self.remote_path_corpus_bundle
        print("Uploading file %s -> %s" % (zip_dest, remote_key.name))
        remote_key.set_contents_from_filename(zip_dest)
        os.remove(zip_dest)

        remote_path = self.remote_path_corpus
        remote_files = [key.name.replace(remote_path, "", 1) for key in list(self.bucket.list(remote_path))]

        upload_list = []
        delete_list = []

        for test_file in test_files:
            if test_file not in remote_files:
                upload_list.append(os.path.join(corpus_dir, test_file))

        if corpus_delete:
            for remote_file in remote_files:
                if remote_file not in test_files:
                    delete_list.append(remote_path + remote_file)

        for upload_file in upload_list:
            remote_key = Key(self.bucket)
            remote_key.name = remote_path + os.path.basename(upload_file)
            print("Uploading file %s -> %s" % (upload_file, remote_key.name))
            remote_key.set_contents_from_filename(upload_file)

        if corpus_delete:
            self.bucket.delete_keys(delete_list, quiet=True)

    def __get_machine_id(self, base_dir, refresh=False):
        '''
        Get (and if necessary generate) the machine id which is based on
        the current timestamp and the hostname of the machine. The
        generated ID is cached inside the base directory, so all
        future calls to this method return the same ID.

        @type base_dir: String
        @param base_dir: Base directory

        @type refresh: bool
        @param refresh: Force generating a new machine ID

        @rtype: String
        @return: The generated/cached machine ID
        '''
        id_file = os.path.join(base_dir, "s3_id")

        # We initially create a unique ID based on the hostname and the
        # current timestamp, then we store this ID in a file inside the
        # fuzzing working directory so we can retrieve it later.
        if refresh or not os.path.exists(id_file):
            h = hashlib.new('sha1')
            h.update(platform.node().encode('utf-8'))
            h.update(str(time.time()).encode('utf-8'))
            id = h.hexdigest()
            with open(id_file, 'w') as id_fd:
                id_fd.write(id)
            return id
        else:
            with open(id_file, 'r') as id_fd:
                return id_fd.read()

    def __upload_queue_files(self, queue_basedir, queue_files, base_dir, cmdline_file):
        machine_id = self.__get_machine_id(base_dir)
        remote_path = "%s%s/" % (self.remote_path_queues, machine_id)
        remote_files = [key.name.replace(remote_path, "", 1) for key in list(self.bucket.list(remote_path))]

        if "closed" in remote_files:
            # The queue we are assigned has been closed remotely.
            # Switch to a new queue instead.
            print("Remote queue %s closed, switching to new queue..." % machine_id)
            machine_id = self.__get_machine_id(base_dir, refresh=True)
            remote_path = "%s%s/" % (self.remote_path_queues, machine_id)
            remote_files = [key.name.replace(remote_path, "", 1) for key in list(self.bucket.list(remote_path))]

        upload_list = []

        for queue_file in queue_files:
            if queue_file not in remote_files:
                upload_list.append(os.path.join(queue_basedir, queue_file))

        if "cmdline" not in remote_files:
            upload_list.append(cmdline_file)

        for upload_file in upload_list:
            remote_key = Key(self.bucket)
            remote_key.name = remote_path + os.path.basename(upload_file)
            print("Uploading file %s -> %s" % (upload_file, remote_key.name))
            try:
                remote_key.set_contents_from_filename(upload_file)
            except IOError:
                # Newer libFuzzer can delete files from the corpus if it finds a shorter version in the same run.
                pass
