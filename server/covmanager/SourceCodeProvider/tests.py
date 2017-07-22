'''
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

import json
import os
import unittest

from GITSourceCodeProvider import GITSourceCodeProvider

class TestGITSourceCodeProvider(unittest.TestCase):
    def setUp(self):
        self.location = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test-git")
        os.rename(os.path.join(self.location, "git"), os.path.join(self.location, ".git"))

    def tearDown(self):
        os.rename(os.path.join(self.location, ".git"), os.path.join(self.location, "git"))

    def runTest(self):
        provider = GITSourceCodeProvider(self.location)

        tests = {
            "a.txt" : {
                "dcbe8ca3dafb34bc90984fb1d74305baf2c58f17" : "Hello world\n",
                "474f46342c82059a819ce7cd3d5e3e0695b9b737" : "I'm sorry Dave,\nI'm afraid I can't do that.\n"
            },
            "abc/def.txt" : {
                "deede1283a224184f6654027e23b654a018e81b0" : "Hi there!\n\nI'm a multi-line file,\n\nnice to meet you.\n",
                "474f46342c82059a819ce7cd3d5e3e0695b9b737" : "Hi there!\n\nI'm a multi-line file,\n\nnice to meet you.\n"
            }
        }

        for filename in tests:
            for revision in tests[filename]:
                self.assertTrue(provider.testRevision(revision), "Revision %s is unknown" % revision)
                self.assertEqual(provider.getSource(filename, revision), tests[filename][revision])

if __name__ == "__main__":
    unittest.main()
