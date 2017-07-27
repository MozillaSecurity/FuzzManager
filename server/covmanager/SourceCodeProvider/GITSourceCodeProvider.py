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
from __future__ import print_function

from datetime import datetime
from django.forms.models import model_to_dict
from django.shortcuts import render, get_object_or_404
import json
import os
import re

import subprocess

from SourceCodeProvider import SourceCodeProvider, UnknownRevisionException, UnknownFilenameException

class GITSourceCodeProvider(SourceCodeProvider):
    def __init__(self, location):
        super(GITSourceCodeProvider, self).__init__(location)

    def getSource(self, filename, revision):
        try:
            return subprocess.check_output(["git", "show", "%s:%s" % (revision, filename)], cwd=self.location)
        except subprocess.CalledProcessError:
            # Check if we can just run show on the revision
            if subprocess.call(["git", "show", revision], cwd=self.location) > 0:
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

