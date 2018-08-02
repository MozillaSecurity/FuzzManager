'''
GIT Source Code Provider

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function, unicode_literals

import subprocess

from .SourceCodeProvider import SourceCodeProvider, UnknownRevisionException, UnknownFilenameException


class GITSourceCodeProvider(SourceCodeProvider):
    def __init__(self, location):
        super(GITSourceCodeProvider, self).__init__(location)

    def getSource(self, filename, revision):
        try:
            return subprocess.check_output(["git", "show", "%s:%s" % (revision, filename)],
                                           cwd=self.location).decode('utf-8')
        except subprocess.CalledProcessError:
            # Check if the revision exists to determine which exception to raise
            if not self.testRevision(revision):
                raise UnknownRevisionException

            # Otherwise assume the file doesn't exist
            raise UnknownFilenameException

    def testRevision(self, revision):
        try:
            subprocess.check_output(["git", "show", revision], cwd=self.location, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            return False
        return True

    def update(self):
        # TODO: This will fail without remotes
        subprocess.check_call(["git", "fetch"], cwd=self.location)

    def getParents(self, revision):
        try:
            output = subprocess.check_output(["git", "log", revision, "--format=%P"], cwd=self.location)
        except subprocess.CalledProcessError:
            raise UnknownRevisionException

        output = output.decode('utf-8').splitlines()

        # No parents
        if not output[0]:
            return []

        return output[0].split(" ")

    def getUnifiedDiff(self, revision):
        # TODO: Implement this method for GIT
        pass

    def checkRevisionsEquivalent(self, revisionA, revisionB):
        # We do not implement any kind of revision equivalence
        # for GIT other than equality.
        return revisionA == revisionB
