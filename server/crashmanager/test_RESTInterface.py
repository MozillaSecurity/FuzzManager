'''
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

import unittest
import requests
from requests.exceptions import ConnectionError

# Server and credentials (user/password) used for testing
# IMPORTANT: In order for these tests to work, you must adjust
# the credentials and auth token here to your own test setup,
# otherwise authentication will fail.
testServerURL = "http://127.0.0.1:8000/crashmanager/rest/"
testAuthCreds = ("admin", "admin")
testAuthToken = "1d7c831476c010645cf107c1b269366335a50f33"

# Check if we have a remote server for testing, if not, skip tests
haveServer = True
try:
    requests.get(testServerURL)
except ConnectionError as e:
    haveServer = False


@unittest.skipIf(not haveServer, reason="No remote server available for testing")
class TestRESTCrashEntryInterface(unittest.TestCase):
    def runTest(self):
        url = testServerURL + "crashes/"

        # Must yield forbidden without authentication
        self.assertEqual(requests.get(url).status_code, requests.codes["unauthorized"])
        self.assertEqual(requests.post(url, {}).status_code, requests.codes["unauthorized"])
        self.assertEqual(requests.put(url, {}).status_code, requests.codes["unauthorized"])

        # Retry with authentication
        response = requests.get(url, headers=dict(Authorization="Token %s" % testAuthToken))

        # Must be empty now
        self.assertEqual(response.status_code, requests.codes["ok"])
        lengthBeforePost = len(response.json())
        #self.assertEqual(response.json(), [])

        data = {
            "rawStdout": "data on\nstdout",
            "rawStderr": "data on\nstderr",
            "rawCrashData": "some\ncrash\ndata",
            "testcase": "foo();\ntest();",
            "testcase_isbinary": False,
            "testcase_quality": 0,
            "testcase_ext": "js",
            "platform": "x86",
            "product": "mozilla-central",
            "product_version": "ba0bc4f26681",
            "os": "linux",
            "client": "client1",
            "tool": "tool1",
        }

        self.assertEqual(requests.post(url, data, headers=dict(Authorization="Token %s" % testAuthToken)).status_code,
                         requests.codes["created"])
        response = requests.get(url, headers=dict(Authorization="Token %s" % testAuthToken))

        json = response.json()
        self.assertEqual(len(json), lengthBeforePost + 1)
        self.assertEqual(json[lengthBeforePost]["product_version"], "ba0bc4f26681")


@unittest.skipIf(not haveServer, reason="No remote server available for testing")
class TestRESTSignatureInterface(unittest.TestCase):
    def runTest(self):
        url = testServerURL + "signatures/"

        # Must yield forbidden without authentication
        self.assertEqual(requests.get(url).status_code, requests.codes["not_found"])


if __name__ == "__main__":
    unittest.main()
