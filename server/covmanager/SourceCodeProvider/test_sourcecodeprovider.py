'''
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

import os
import unittest

from .GITSourceCodeProvider import GITSourceCodeProvider
from .HGSourceCodeProvider import HGSourceCodeProvider
from .SourceCodeProvider import Utils


class TestGITSourceCodeProvider(unittest.TestCase):
    def setUp(self):
        self.location = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test-git")
        os.rename(os.path.join(self.location, "git"), os.path.join(self.location, ".git"))

    def tearDown(self):
        os.rename(os.path.join(self.location, ".git"), os.path.join(self.location, "git"))

    def runTest(self):
        provider = GITSourceCodeProvider(self.location)

        tests = {
            "a.txt": {
                "dcbe8ca3dafb34bc90984fb1d74305baf2c58f17": "Hello world\n",
                "474f46342c82059a819ce7cd3d5e3e0695b9b737": "I'm sorry Dave,\nI'm afraid I can't do that.\n"
            },
            "abc/def.txt": {
                "deede1283a224184f6654027e23b654a018e81b0": ("Hi there!\n\nI'm a multi-line file,\n\n"
                                                             "nice to meet you.\n"),
                "474f46342c82059a819ce7cd3d5e3e0695b9b737": "Hi there!\n\nI'm a multi-line file,\n\nnice to meet you.\n"
            }
        }

        for filename in tests:
            for revision in tests[filename]:
                self.assertTrue(provider.testRevision(revision), "Revision %s is unknown" % revision)
                self.assertEqual(provider.getSource(filename, revision), tests[filename][revision])

        parents = provider.getParents("deede1283a224184f6654027e23b654a018e81b0")
        self.assertEqual(len(parents), 1)
        self.assertEqual(parents[0], "dcbe8ca3dafb34bc90984fb1d74305baf2c58f17")

        parents = provider.getParents("dcbe8ca3dafb34bc90984fb1d74305baf2c58f17")
        self.assertEqual(len(parents), 0)


class TestHGSourceCodeProvider(unittest.TestCase):
    def setUp(self):
        self.location = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test-hg")
        os.rename(os.path.join(self.location, "hg"), os.path.join(self.location, ".hg"))

    def tearDown(self):
        os.rename(os.path.join(self.location, ".hg"), os.path.join(self.location, "hg"))

    def runTest(self):
        provider = HGSourceCodeProvider(self.location)

        tests = {
            "a.txt": {
                "c3abaa766d52f438219920d37461b341321d4fef": "Hello world\n",
                "c179ace9e260adbabd17426750b5a62403691624": "I'm sorry Dave,\nI'm afraid I can't do that.\n"
            },
            "abc/def.txt": {
                "05ceb4ce5ed96a107fb40e3b39df7da18f0780c3": ("Hi there!\n\nI'm a multi-line file,\n\n"
                                                             "nice to meet you.\n"),
                "c179ace9e260adbabd17426750b5a62403691624": "Hi there!\n\nI'm a multi-line file,\n\nnice to meet you.\n"
            }
        }

        for filename in tests:
            for revision in tests[filename]:
                self.assertTrue(provider.testRevision(revision), "Revision %s is unknown" % revision)
                self.assertEqual(provider.getSource(filename, revision), tests[filename][revision])

        parents = provider.getParents("7a6e60cac455")
        self.assertEqual(len(parents), 1)
        self.assertEqual(parents[0], "05ceb4ce5ed96a107fb40e3b39df7da18f0780c3")

        parents = provider.getParents("c3abaa766d52")
        self.assertEqual(len(parents), 0)


@unittest.skipIf(not os.path.isdir("/home/decoder/Mozilla/repos/mozilla-central-fm"), reason="not decoder")
class TestHGDiff(unittest.TestCase):
    def runTest(self):
        provider = HGSourceCodeProvider("/home/decoder/Mozilla/repos/mozilla-central-fm")
        diff = provider.getUnifiedDiff("4f8e0cb21016")

        print(Utils.getDiffLocations(diff))


if __name__ == "__main__":
    unittest.main()
