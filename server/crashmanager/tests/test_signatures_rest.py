# coding: utf-8
'''Tests for Buckets rest api.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import json
import logging
import pytest
import requests


# What should be allowed:
#
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# |        |      |          | no auth | no perm | unrestricted | unrestricted      | restricted | restricted        |
# |        |      |          |         |         |              | ignore_toolfilter |            | ignore_toolfilter |
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# | GET    | /    | list     | 401     | 403     | toolfilter   | all               | toolfilter | toolfilter        |
# |        +------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# |        | /id/ | retrieve | 401     | 403     | all          | all               | toolfilter | toolfilter        |
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# | POST   | /    | create   | 401     | 403     | all (TODO)   | all (TODO)        | all (TODO) | all (TODO)        |
# |        +------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# |        | /id/ | -        | 401     | 403     | 405          | 405               | 405        | 405               |
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# | PUT    | /    | -        | 401     | 403     | 405          | 405               | 405        | 405               |
# |        +------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# |        | /id/ | -        | 401     | 403     | 405          | 405               | 405        | 405               |
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# | PATCH  | /    | -        | 401     | 403     | 405          | 405               | 405        | 405               |
# |        +------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# |        | /id/ | update   | 401     | 403     | all (TODO)   | all (TODO)        | 405        | 405               |
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# | DELETE | /    | -        | 401     | 403     | 405          | 405               | 405        | 405               |
# |        +------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# |        | /id/ | delete   | 401     | 403     | all (TODO)   | all (TODO)        | 405        | 405               |
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+


LOG = logging.getLogger("fm.crashmanager.tests.signatures.rest")


def _compare_rest_result_to_bucket(result, bucket, size, quality):
    assert set(result) == {'best_quality', 'bug', 'frequent', 'id', 'permanent', 'shortDescription',
                           'signature', 'size'}
    assert result["id"] == bucket.pk
    assert result["best_quality"] == quality
    assert result["bug"] == bucket.bug_id
    assert result["frequent"] == bucket.frequent
    assert result["permanent"] == bucket.permanent
    assert result["shortDescription"] == bucket.shortDescription
    assert result["signature"] == bucket.signature
    assert result["size"] == size


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
@pytest.mark.parametrize("url", ["/crashmanager/rest/buckets/", "/crashmanager/rest/buckets/1/"])
def test_rest_signatures_no_auth(db, api_client, method, url):
    """must yield unauthorized without authentication"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes['unauthorized']


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
@pytest.mark.parametrize("url", ["/crashmanager/rest/buckets/", "/crashmanager/rest/buckets/1/"])
def test_rest_signatures_no_perm(user_noperm, api_client, method, url):
    """must yield forbidden without permission"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes['forbidden']


@pytest.mark.parametrize("method, url, user", [
    ("delete", "/crashmanager/rest/buckets/", "normal"),
    ("delete", "/crashmanager/rest/buckets/", "restricted"),
    ("delete", "/crashmanager/rest/buckets/1/", "normal"),  # TODO: this should be allowed, but hasn't been implemented
    ("delete", "/crashmanager/rest/buckets/1/", "restricted"),
    ("patch", "/crashmanager/rest/buckets/", "normal"),
    ("patch", "/crashmanager/rest/buckets/", "restricted"),
    ("patch", "/crashmanager/rest/buckets/1/", "normal"),  # TODO: this should be allowed, but hasn't been implemented
    ("patch", "/crashmanager/rest/buckets/1/", "restricted"),
    ("post", "/crashmanager/rest/buckets/", "normal"),  # TODO: this should be allowed, but hasn't been implemented
    ("post", "/crashmanager/rest/buckets/", "restricted"),  # TODO: this should be allowed, but hasn't been implemented
    ("post", "/crashmanager/rest/buckets/1/", "normal"),
    ("post", "/crashmanager/rest/buckets/1/", "restricted"),
    ("put", "/crashmanager/rest/buckets/", "normal"),
    ("put", "/crashmanager/rest/buckets/", "restricted"),
    ("put", "/crashmanager/rest/buckets/1/", "normal"),
    ("put", "/crashmanager/rest/buckets/1/", "restricted"),
], indirect=["user"])
def test_rest_signatures_methods(api_client, user, method, url):
    """must yield method-not-allowed for unsupported methods"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes['method_not_allowed']


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
@pytest.mark.parametrize("ignore_toolfilter", [True, False])
def test_rest_signatures_list(api_client, cm, user, ignore_toolfilter):
    """test that buckets can be listed"""
    bucket1 = cm.create_bucket(shortDescription="bucket #1")
    bucket2 = cm.create_bucket(shortDescription="bucket #2")
    buckets = [bucket1, bucket2, bucket1, bucket1]
    tests = [cm.create_testcase("test1.txt", quality=1),
             cm.create_testcase("test2.txt", quality=9),
             cm.create_testcase("test3.txt", quality=2),
             cm.create_testcase("test4.txt", quality=3)]
    tools = ["tool2", "tool2", "tool1", "tool1"]
    for i in range(4):
        cm.create_crash(shortSignature="crash #%d" % (i + 1),
                        client="client #%d" % (i + 1),
                        os="os #%d" % (i + 1),
                        product="product #%d" % (i + 1),
                        product_version="%d" % (i + 1),
                        platform="platform #%d" % (i + 1),
                        tool=tools[i],
                        testcase=tests[i],
                        bucket=buckets[i])
    # Create toolfilter, check that query returns only tool-filtered crashes
    cm.create_toolfilter('tool1', user=user.username)
    params = {}
    if ignore_toolfilter:
        params["ignore_toolfilter"] = "1"
    resp = api_client.get('/crashmanager/rest/buckets/', params)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()) == {'count', 'next', 'previous', 'results'}
    expected_buckets = 2 if ignore_toolfilter and user.username == "test" else 1
    assert resp['count'] == expected_buckets
    assert resp['next'] is None
    assert resp['previous'] is None
    resp = resp['results']
    assert len(resp) == expected_buckets
    resp = sorted(resp, key=lambda x: x["id"])
    if ignore_toolfilter and user.username == "test":
        _compare_rest_result_to_bucket(resp[0], bucket1, 3, 1)
        _compare_rest_result_to_bucket(resp[1], bucket2, 1, 9)
    else:
        _compare_rest_result_to_bucket(resp[0], bucket1, 2, 2)


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
@pytest.mark.parametrize("ignore_toolfilter", [True, False])
def test_rest_signatures_retrieve(api_client, cm, user, ignore_toolfilter):
    """test that individual Signature can be fetched"""
    bucket1 = cm.create_bucket(shortDescription="bucket #1")
    bucket2 = cm.create_bucket(shortDescription="bucket #2")
    tests = [cm.create_testcase("test1.txt", quality=9),
             None,
             cm.create_testcase("test3.txt", quality=2),
             cm.create_testcase("test4.txt", quality=3)]
    buckets = [bucket1, bucket1, bucket2, bucket2]
    tools = ["tool1", "tool2", "tool2", "tool3"]
    for i in range(4):
        cm.create_crash(shortSignature="crash #%d" % (i + 1),
                        client="client #%d" % (i + 1),
                        os="os #%d" % (i + 1),
                        product="product #%d" % (i + 1),
                        product_version="%d" % (i + 1),
                        platform="platform #%d" % (i + 1),
                        tool=tools[i],
                        testcase=tests[i],
                        bucket=buckets[i])
    cm.create_toolfilter('tool1', user=user.username)
    params = {}
    if ignore_toolfilter:
        params["ignore_toolfilter"] = "1"
    for i, bucket in enumerate([bucket1, bucket2]):
        resp = api_client.get('/crashmanager/rest/buckets/%d/' % bucket.pk, params)
        LOG.debug(resp)
        allowed = user.username == "test" or i == 0  # only unrestricted user, or in-toolfilter
        if not allowed:
            assert resp.status_code == requests.codes['not_found']
        else:
            status_code = resp.status_code
            resp = resp.json()
            assert status_code == requests.codes['ok'], resp['detail']
            if user.username == "test":
                if ignore_toolfilter:
                    size, quality = [(2, 9), (2, 2)][i]
                else:
                    size, quality = [(1, 9), (0, None)][i]
            else:
                size, quality = (1, 9)
            _compare_rest_result_to_bucket(resp, bucket, size, quality)
