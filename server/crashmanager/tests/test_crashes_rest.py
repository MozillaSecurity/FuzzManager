"""Tests for Crashes rest api.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import json
import logging
import os.path
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests
from django.utils.http import urlencode

from crashmanager.models import BucketStatistics, CrashEntry
from crashmanager.models import TestCase as cmTestCase

# What should be allowed:
#
# +--------+------+----------+---------+---------+--------------+-------------------+
# |        |      |          | no auth | no perm | unrestricted | unrestricted,     |
# |        |      |          |         |         |              | ignore_toolfilter |
# +--------+------+----------+---------+---------+--------------+-------------------+
# | GET    | /    | list     | 401     | 403     | toolfilter   | all               |
# |        +------+----------+---------+---------+--------------+-------------------+
# |        | /id/ | retrieve | 401     | 403     | all          | all               |
# +--------+------+----------+---------+---------+--------------+-------------------+
# | POST   | /    | create   | 401     | 403     | all          | all               |
# |        +------+----------+---------+---------+--------------+-------------------+
# |        | /id/ | -        | 401     | 403     | 405          | 405               |
# +--------+------+----------+---------+---------+--------------+-------------------+
# | PUT    | /    | -        | 401     | 403     | 405          | 405               |
# |        +------+----------+---------+---------+--------------+-------------------+
# |        | /id/ | -        | 401     | 403     | 405          | 405               |
# +--------+------+----------+---------+---------+--------------+-------------------+
# | PATCH  | /    | -        | 401     | 403     | 405          | 405               |
# |        +------+----------+---------+---------+--------------+-------------------+
# |        | /id/ | update   | 401     | 403     | all          | all               |
# +--------+------+----------+---------+---------+--------------+-------------------+
# | DELETE | /    | bulk del | 401     | 403     | toolfilter   | all               |
# |        +------+----------+---------+---------+--------------+-------------------+
# |        | /id/ | delete   | 401     | 403     | all (TODO)   | all (TODO)        |
# +--------+------+----------+---------+---------+--------------+-------------------+
#
# +--------+------+----------+------------+-------------------+
# |        |      |          | restricted | restricted,       |
# |        |      |          |            | ignore_toolfilter |
# +--------+------+----------+------------+-------------------+
# | GET    | /    | list     | toolfilter | toolfilter        |
# |        +------+----------+------------+-------------------+
# |        | /id/ | retrieve | toolfilter | toolfilter        |
# +--------+------+----------+------------+-------------------+
# | POST   | /    | create   | all        | all               |
# |        +------+----------+------------+-------------------+
# |        | /id/ | -        | 405        | 405               |
# +--------+------+----------+------------+-------------------+
# | PUT    | /    | -        | 405        | 405               |
# |        +------+----------+------------+-------------------+
# |        | /id/ | -        | 405        | 405               |
# +--------+------+----------+------------+-------------------+
# | PATCH  | /    | -        | 405        | 405               |
# |        +------+----------+------------+-------------------+
# |        | /id/ | update   | 405        | 405               |
# +--------+------+----------+------------+-------------------+
# | DELETE | /    | bulk del | 405        | 405               |
# |        +------+----------+------------+-------------------+
# |        | /id/ | delete   | 405        | 405               |
# +--------+------+----------+------------+-------------------+


FIXTURE_PATH = Path(__file__).parent / "fixtures"
LOG = logging.getLogger("fm.crashmanager.tests.crashes.rest")


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
@pytest.mark.parametrize(
    "url", ["/crashmanager/rest/crashes/", "/crashmanager/rest/crashes/1/"]
)
def test_rest_crashes_no_auth(db, api_client, method, url):
    """must yield unauthorized without authentication"""
    assert (
        getattr(api_client, method)(url, {}).status_code
        == requests.codes["unauthorized"]
    )


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
@pytest.mark.parametrize(
    "url", ["/crashmanager/rest/crashes/", "/crashmanager/rest/crashes/1/"]
)
@pytest.mark.parametrize("user", ["noperm", "only_sigs", "only_report"], indirect=True)
def test_rest_crashes_no_perm(user, api_client, method, url):
    """must yield forbidden without permission"""
    if (
        url.endswith("crashes/")
        and method == "post"
        and user.username == "test-only-report"
    ):
        pytest.skip()
    assert (
        getattr(api_client, method)(url, {}).status_code == requests.codes["forbidden"]
    )


@pytest.mark.parametrize(
    "method, url, user",
    [
        ("delete", "/crashmanager/rest/crashes/", "restricted"),
        (
            "delete",
            "/crashmanager/rest/crashes/1/",
            "normal",
        ),  # TODO: this should be allowed, but hasn't been implemented
        ("delete", "/crashmanager/rest/crashes/1/", "restricted"),
        ("patch", "/crashmanager/rest/crashes/", "normal"),
        ("patch", "/crashmanager/rest/crashes/", "restricted"),
        ("patch", "/crashmanager/rest/crashes/1/", "restricted"),
        ("post", "/crashmanager/rest/crashes/1/", "normal"),
        ("post", "/crashmanager/rest/crashes/1/", "restricted"),
        ("put", "/crashmanager/rest/crashes/", "normal"),
        ("put", "/crashmanager/rest/crashes/", "restricted"),
        ("put", "/crashmanager/rest/crashes/1/", "normal"),
        ("put", "/crashmanager/rest/crashes/1/", "restricted"),
    ],
    indirect=["user"],
)
def test_rest_crashes_methods(api_client, user, method, url):
    """must yield method-not-allowed for unsupported methods"""
    assert (
        getattr(api_client, method)(url, {}).status_code
        == requests.codes["method_not_allowed"]
    )


def _compare_rest_result_to_crash(result, crash, raw=True):
    expected_fields = {
        "args",
        "bucket",
        "client",
        "env",
        "id",
        "metadata",
        "os",
        "platform",
        "product",
        "product_version",
        "testcase",
        "testcase_isbinary",
        "testcase_quality",
        "testcase_size",
        "tool",
        "shortSignature",
        "crashAddress",
        "triagedOnce",
        "created",
    }
    if raw:
        expected_fields |= {"rawCrashData", "rawStderr", "rawStdout"}
    assert set(result) == expected_fields
    for key, value in result.items():
        if key == "testcase":
            continue
        attrs = {
            "client": "client_name",
            "bucket": "bucket_pk",
            "os": "os_name",
            "platform": "platform_name",
            "product": "product_name",
            "testcase_isbinary": "testcase_isBinary",
            "tool": "tool_name",
        }.get(key, key)
        obj = crash
        for attr in attrs.split("_"):
            if obj is not None:
                obj = getattr(obj, attr)
        if isinstance(obj, datetime):
            obj = obj.isoformat().replace("+00:00", "Z")
        assert value == obj


def _compare_created_data_to_crash(
    data, crash, crash_address=None, short_signature=None
):
    for field in ("rawStdout", "rawStderr", "rawCrashData"):
        assert getattr(crash, field) == data[field].strip()
    if "testcase" in data:
        expected_ext = data.get("testcase_ext", "")
        assert os.path.splitext(crash.testcase.test.path)[1].lstrip(".") == expected_ext
        with open(crash.testcase.test.path) as fp:
            assert fp.read() == data["testcase"]
        assert crash.testcase.isBinary == data["testcase_isbinary"]
        assert crash.testcase.quality == data["testcase_quality"]
    else:
        assert crash.testcase is None
    for field in ("platform", "product", "os", "client", "tool"):
        assert getattr(crash, field).name == data[field]
    assert crash.product.version == data["product_version"]
    if crash_address is not None:
        assert crash.crashAddress == crash_address
    if short_signature is not None:
        assert crash.shortSignature == short_signature


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
@pytest.mark.parametrize("ignore_toolfilter", [True, False])
@pytest.mark.parametrize("include_raw", [True, False])
def test_rest_crashes_list(api_client, user, cm, ignore_toolfilter, include_raw):
    """test that list returns the right crashes"""
    # if restricted or normal, must only list crashes in toolfilter
    buckets = [cm.create_bucket(shortDescription="bucket #1"), None]
    testcases = [
        cm.create_testcase("test3.txt", quality=5),
        cm.create_testcase("test4.txt", quality=5),
    ]
    tools = ["tool2", "tool1"]
    crashes = [
        cm.create_crash(
            shortSignature="crash #%d" % (i + 1),
            client="client #%d" % (i + 1),
            os="os #%d" % (i + 1),
            product="product #%d" % (i + 1),
            product_version="%d" % (i + 1),
            platform="platform #%d" % (i + 1),
            tool=tools[i],
            bucket=buckets[i],
            testcase=testcases[i],
        )
        for i in range(2)
    ]
    # Create toolfilter, check that query returns only tool-filtered crashes
    cm.create_toolfilter("tool2", user=user.username)
    params = {}
    if ignore_toolfilter:
        params["ignore_toolfilter"] = "1"
    if not include_raw:
        params["include_raw"] = "0"
    resp = api_client.get("/crashmanager/rest/crashes/", params)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    expected = 2 if ignore_toolfilter and user.username == "test" else 1
    assert resp.status_code == requests.codes["ok"]
    resp = json.loads(resp.content.decode("utf-8"))
    assert set(resp) == {"count", "next", "previous", "results"}
    assert resp["count"] == expected
    assert resp["next"] is None
    assert resp["previous"] is None
    assert len(resp["results"]) == expected
    for result, crash in zip(resp["results"], crashes[:expected]):
        _compare_rest_result_to_crash(result, crash, raw=include_raw)


@pytest.mark.parametrize("ignore_toolfilter", [True, False])
def test_rest_crashes_delete(api_client, user_normal, cm, ignore_toolfilter, mocker):
    """test that delete crashes api works as expected"""
    testcases = [
        cm.create_testcase("test3.txt", quality=5),
        cm.create_testcase("test4.txt", quality=5),
    ]
    tools = ["tool2", "tool1"]
    for i in range(2):
        cm.create_crash(
            shortSignature=f"crash #{i + 1}",
            client=f"client #{i + 1}",
            os=f"os #{i + 1}",
            product=f"product #{i + 1}",
            product_version=f"{i + 1}",
            platform=f"platform #{i + 1}",
            tool=tools[i],
            testcase=testcases[i],
        )
    # Create toolfilter, check that delete affects only tool-filtered crashes
    cm.create_toolfilter("tool2", user=user_normal.username)
    params = {}
    if ignore_toolfilter:
        params["ignore_toolfilter"] = "1"

    # DRF APIClient only handles URL params for GET
    # for DELETE, have to build them ourselves
    query_string = urlencode(params, doseq=True)

    resp = api_client.delete("/crashmanager/rest/crashes/", QUERY_STRING=query_string)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    expected = 2 if ignore_toolfilter else 1
    assert resp.json() == {
        "deleted": expected,
        "nextOffset": None,
        "total": expected,
    }
    crashes = CrashEntry.objects.all()
    if ignore_toolfilter:
        # all crashes deleted
        assert crashes.count() == 0
    else:
        # crashes not in toolfilter remain
        assert crashes.count() == 1
        entry = crashes.get()
        assert entry.tool.name == "tool1"


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
@pytest.mark.parametrize("ignore_toolfilter", [True, False])
@pytest.mark.parametrize("include_raw", [True, False])
def test_rest_crashes_retrieve(api_client, user, cm, ignore_toolfilter, include_raw):
    """test that retrieve returns the right crash"""
    # if restricted or normal, must only list crashes in toolfilter
    buckets = [cm.create_bucket(shortDescription="bucket #1"), None]
    testcases = [
        cm.create_testcase("test3.txt", quality=5),
        cm.create_testcase("test4.txt", quality=5),
    ]
    tools = ["tool2", "tool1"]
    crashes = [
        cm.create_crash(
            shortSignature="crash #%d" % (i + 1),
            client="client #%d" % (i + 1),
            os="os #%d" % (i + 1),
            product="product #%d" % (i + 1),
            product_version="%d" % (i + 1),
            platform="platform #%d" % (i + 1),
            tool=tools[i],
            bucket=buckets[i],
            testcase=testcases[i],
        )
        for i in range(2)
    ]
    # Create toolfilter, check that query returns only tool-filtered crashes
    cm.create_toolfilter("tool2", user=user.username)
    params = {}
    if ignore_toolfilter:
        params["ignore_toolfilter"] = "1"
    if not include_raw:
        params["include_raw"] = "0"
    for i, crash in enumerate(crashes):
        resp = api_client.get("/crashmanager/rest/crashes/%d/" % crash.pk, params)
        LOG.debug(resp)
        allowed = user.username == "test" or tools[i] == "tool2"
        if not allowed:
            assert resp.status_code == requests.codes["not_found"]
        else:
            status_code = resp.status_code
            resp = resp.json()
            assert status_code == requests.codes["ok"], resp["detail"]
            _compare_rest_result_to_crash(resp, crash, raw=include_raw)


@pytest.mark.parametrize(
    "user, expected, toolfilter",
    [
        ("normal", 3, None),
        ("restricted", None, None),
        ("restricted", 3, "tool1"),
    ],
    indirect=["user"],
)
def test_rest_crashes_list_query(api_client, cm, user, expected, toolfilter):
    """test that crashes can be queried"""
    buckets = [cm.create_bucket(shortDescription="bucket #1"), None, None, None]
    testcases = [
        cm.create_testcase("test1.txt", quality=5),
        cm.create_testcase("test2.txt", quality=0),
        cm.create_testcase("test3.txt", quality=5),
        cm.create_testcase("test4.txt", quality=5),
    ]
    tools = ["tool1", "tool1", "tool2", "tool1"]
    crashes = [
        cm.create_crash(
            shortSignature="crash #%d" % (i + 1),
            client="client #%d" % (i + 1),
            os="os #%d" % (i + 1),
            product="product #%d" % (i + 1),
            product_version="%d" % (i + 1),
            platform="platform #%d" % (i + 1),
            tool=tools[i],
            bucket=buckets[i],
            testcase=testcases[i],
        )
        for i in range(4)
    ]
    if toolfilter is not None:
        cm.create_toolfilter(toolfilter, user=user.username)
    resp = api_client.get(
        "/crashmanager/rest/crashes/",
        {
            "query": json.dumps(
                {
                    "op": "AND",
                    "bucket": None,
                    "testcase__quality": 5,
                    "tool__name__in": ["tool1"],
                }
            )
        },
    )
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    resp = json.loads(resp.content.decode("utf-8"))
    assert set(resp) == {"count", "next", "previous", "results"}
    assert resp["count"] == (0 if expected is None else 1)
    assert resp["next"] is None
    assert resp["previous"] is None
    assert len(resp["results"]) == resp["count"]
    if expected is not None:
        _compare_rest_result_to_crash(resp["results"][0], crashes[expected])


@pytest.mark.parametrize("user", ["normal", "restricted", "only_report"], indirect=True)
@pytest.mark.parametrize(
    "data",
    [
        # simple create
        {
            "rawStdout": "data on\nstdout",
            "rawStderr": "data on\nstderr",
            "rawCrashData": "some\tcrash\ndata\n",
            "testcase": "foo();\ntest();",
            "testcase_isbinary": False,
            "testcase_quality": 0,
            "testcase_ext": "js",
            "platform": "x86",
            "product": "mozilla-central",
            "product_version": "badf00d",
            "os": "linux",
            "client": "client1",
            "tool": "tool1",
        },
        # crash reporting works with no testcase
        {
            "rawStdout": "data on\nstdout",
            "rawStderr": "data on\nstderr",
            "rawCrashData": "some\ncrash\ndata",
            "platform": "x86",
            "product": "mozilla-central",
            "product_version": "badf00d",
            "os": "linux",
            "client": "client1",
            "tool": "tool1",
            "testcase_ext": "js",
        },
        # crash reporting works with empty fields where allowed
        {
            "rawStdout": "",
            "rawStderr": "",
            "rawCrashData": "",
            "testcase": "blah",
            "testcase_isbinary": False,
            "testcase_quality": 0,
            "platform": "x",
            "product": "x",
            "product_version": "",
            "os": "x",
            "client": "x",
            "tool": "x",
        },
    ],
)
def test_rest_crashes_report_crash(api_client, user, data, user_restricted_with_tools):
    """test that crash reporting works"""
    resp = api_client.post("/crashmanager/rest/crashes/", data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["created"]
    crash = CrashEntry.objects.get()
    _compare_created_data_to_crash(data, crash)


def test_rest_crashes_report_crash_long(api_client, user_normal):
    """test that crash reporting works with fields interpreted as `long` in python 2"""
    data = {
        "rawStdout": "",
        "rawStderr": "",
        "rawCrashData": (FIXTURE_PATH / "gdb_crash_data.txt").read_text(),
        "testcase": "blah",
        "testcase_isbinary": False,
        "testcase_quality": 0,
        "platform": "x86_64",
        "product": "x",
        "product_version": "",
        "os": "linux",
        "client": "x",
        "tool": "x",
    }
    resp = api_client.post("/crashmanager/rest/crashes/", data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["created"]
    crash = CrashEntry.objects.get()
    _compare_created_data_to_crash(data, crash, crash_address="0xf7056fff")


@patch(
    "crashmanager.models.CrashEntry.save",
    new=Mock(side_effect=RuntimeError("crashentry failing intentionally")),
)
def test_rest_crashes_report_bad_crash_removes_testcase(api_client, user_normal):
    """test that reporting a bad crash doesn't leave an orphaned testcase"""
    data = {
        "rawStdout": "data on\nstdout",
        "rawStderr": "data on\nstderr",
        "rawCrashData": "some\tcrash\ndata\n",
        "testcase": "foo();\ntest();",
        "testcase_isbinary": False,
        "testcase_quality": 0,
        "testcase_ext": "js",
        "platform": "x86",
        "product": "mozilla-central",
        "product_version": "badf00d",
        "os": "linux",
        "client": "client1",
        "tool": "tool1",
    }
    with pytest.raises(RuntimeError):
        api_client.post("/crashmanager/rest/crashes/", data=data)
    assert not CrashEntry.objects.exists()
    assert not cmTestCase.objects.exists()


def test_rest_crashes_report_crash_long_sig(api_client, user_normal):
    """test that crash reporting works with an assertion message too long for
    shortSignature"""
    data = {
        "rawStdout": "data on\nstdout",
        "rawStderr": "data on\nstderr",
        "rawCrashData": "Assertion failure: " + ("A" * 4096),
        "platform": "x86",
        "product": "mozilla-central",
        "product_version": "badf00d",
        "os": "linux",
        "client": "client1",
        "tool": "tool1",
    }
    resp = api_client.post("/crashmanager/rest/crashes/", data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["created"]
    crash = CrashEntry.objects.get()
    expected = ("Assertion failure: " + ("A" * 4096))[
        : CrashEntry._meta.get_field("shortSignature").max_length
    ]
    _compare_created_data_to_crash(data, crash, short_signature=expected)


@pytest.mark.parametrize("orig_quality, new_quality", ((0, 5), (5, 0)))
def test_rest_crash_update(api_client, cm, orig_quality, new_quality, user_normal):
    """test that only allowed fields of CrashEntry can be updated"""
    test = cm.create_testcase("test.txt", quality=orig_quality)
    bucket = cm.create_bucket(shortDescription="bucket #1")
    crash = cm.create_crash(
        shortSignature="crash #1",
        bucket=bucket,
        client="client #1",
        os="os #1",
        product="product #1",
        product_version="1",
        platform="platform #1",
        tool="tool #1",
        testcase=test,
    )
    fields = {
        "args",
        "bucket",
        "client",
        "env",
        "id",
        "metadata",
        "os",
        "platform",
        "product",
        "product_version",
        "rawCrashData",
        "rawStderr",
        "rawStdout",
        "testcase",
        "testcase_isbinary",
        "tool",
        "shortSignature",
        "crashAddress",
    }
    for field in fields:
        resp = api_client.patch(
            "/crashmanager/rest/crashes/%d/" % crash.pk, {field: ""}
        )
        LOG.debug(resp)
        assert resp.status_code == requests.codes["bad_request"]
    resp = api_client.patch(
        "/crashmanager/rest/crashes/%d/" % crash.pk,
        {"testcase_quality": str(new_quality)},
    )
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    test = cmTestCase.objects.get(pk=test.pk)  # re-read
    assert test.quality == new_quality

    # check that BucketStatistics are updated
    assert (
        BucketStatistics.objects.get(bucket_id=bucket.id, tool_id=crash.tool_id).quality
        == new_quality
    )


def test_rest_crash_update_restricted(api_client, cm, user_restricted):
    """test that restricted users cannot perform updates on CrashEntry"""
    test = cm.create_testcase("test.txt", quality=0)
    bucket = cm.create_bucket(shortDescription="bucket #1")
    crash = cm.create_crash(
        shortSignature="crash #1",
        bucket=bucket,
        client="client #1",
        os="os #1",
        product="product #1",
        product_version="1",
        platform="platform #1",
        tool="tool #1",
        testcase=test,
    )
    fields = {
        "args",
        "bucket",
        "client",
        "env",
        "id",
        "metadata",
        "os",
        "platform",
        "product",
        "product_version",
        "rawCrashData",
        "rawStderr",
        "rawStdout",
        "testcase",
        "testcase_isbinary",
        "testcase_quality",
        "tool",
        "shortSignature",
        "crashAddress",
    }
    for field in fields:
        resp = api_client.patch(
            "/crashmanager/rest/crashes/%d/" % crash.pk, {field: ""}
        )
        LOG.debug(resp)
        assert resp.status_code == requests.codes["method_not_allowed"]
