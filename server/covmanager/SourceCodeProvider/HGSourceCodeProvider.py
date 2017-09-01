'''
HG Source Code Provider

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

import re
import subprocess

from SourceCodeProvider import SourceCodeProvider, UnknownRevisionException, UnknownFilenameException

class HGSourceCodeProvider(SourceCodeProvider):
    def __init__(self, location):
        super(HGSourceCodeProvider, self).__init__(location)

    def getSource(self, filename, revision):
        # Avoid passing in absolute filenames to HG
        if filename.startswith("/"):
            filename = filename[1:]

        try:
            return subprocess.check_output(["hg", "cat", "-r", revision, filename], cwd=self.location)
        except subprocess.CalledProcessError:
            # Check if the revision exists to determine which exception to raise
            if not self.testRevision(revision):
                raise UnknownRevisionException

            # Otherwise assume the file doesn't exist
            raise UnknownFilenameException

    def testRevision(self, revision):
        try:
            subprocess.check_output(["hg", "log", "-r", revision], cwd=self.location, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            return False
        return True

    def update(self):
        # TODO: This will fail without remotes
        subprocess.check_call(["hg", "pull"], cwd=self.location)

    def getParents(self, revision):
        try:
            output = subprocess.check_output(["hg", "log", "-r", revision, "--template", r'{parents}\n', "--debug"], cwd=self.location)
        except subprocess.CalledProcessError:
            raise UnknownRevisionException

        output = output.splitlines()

        parents = []

        for line in output:
            result = re.match(r'\d+:([0-9a-f]+)\s+', line)
            if result:
                parents.append(result.group(1))

        return parents

    def getUnifiedDiff(self, revision):
        try:
            output = subprocess.check_output(["hg", "diff", "--git", "-U0", "-c", revision], cwd=self.location)
        except subprocess.CalledProcessError:
            raise UnknownRevisionException

        return output
