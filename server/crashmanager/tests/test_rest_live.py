# coding: utf-8
'''
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
import pytest
import requests
from six.moves.urllib.parse import urlsplit


pytestmark = pytest.mark.django_db()  # pylint: disable=invalid-name
pytest_plugins = 'server.tests'  # pylint: disable=invalid-name


@pytest.mark.skip
def test_RESTCrashEntryInterface(live_server, fm_user):
    url = urlsplit(live_server.url)
    url = "%s://%s:%s/crashmanager/rest/crashes/" % (url.scheme, url.hostname, url.port)

    # Must yield forbidden without authentication
    assert requests.get(url).status_code == requests.codes["unauthorized"]
    assert requests.post(url, {}).status_code == requests.codes["unauthorized"]
    assert requests.put(url, {}).status_code == requests.codes["unauthorized"]

    # Retry with authentication
    response = requests.get(url, headers=dict(Authorization="Token " + fm_user.token))

    # Must be empty now
    assert response.status_code == requests.codes["ok"]
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

    assert requests.post(url, data, headers=dict(Authorization="Token %s" % fm_user.token)).status_code \
        == requests.codes["created"]
    response = requests.get(url, headers=dict(Authorization="Token %s" % fm_user.token))

    json = response.json()
    assert len(json) == lengthBeforePost + 1
    assert json[lengthBeforePost]["product_version"] == "ba0bc4f26681"


def test_RESTSignatureInterface(live_server):
    url = urlsplit(live_server.url)
    url = "%s://%s:%s/crashmanager/rest/signatures/" % (url.scheme, url.hostname, url.port)

    # Must yield forbidden without authentication
    assert requests.get(url).status_code == requests.codes["not_found"]
