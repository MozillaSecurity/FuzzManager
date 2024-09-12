"""Tests for Reports rest api.

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

from reportmanager.models import ReportEntry
from reportmanager.models import TestCase as cmTestCase

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
LOG = logging.getLogger("fm.reportmanager.tests.reports.rest")


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
@pytest.mark.parametrize(
    "url", ["/reportmanager/rest/reports/", "/reportmanager/rest/reports/1/"]
)
def test_rest_reports_no_auth(db, api_client, method, url):
    """must yield unauthorized without authentication"""
    assert (
        getattr(api_client, method)(url, {}).status_code
        == requests.codes["unauthorized"]
    )


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
@pytest.mark.parametrize(
    "url", ["/reportmanager/rest/reports/", "/reportmanager/rest/reports/1/"]
)
@pytest.mark.usefixtures("user_noperm")
def test_rest_reports_no_perm(api_client, method, url):
    """must yield forbidden without permission"""
    assert (
        getattr(api_client, method)(url, {}).status_code == requests.codes["forbidden"]
    )


@pytest.mark.parametrize(
    "method, url, user",
    [
        ("delete", "/reportmanager/rest/reports/", "restricted"),
        (
            "delete",
            "/reportmanager/rest/reports/1/",
            "normal",
        ),  # TODO: this should be allowed, but hasn't been implemented
        ("delete", "/reportmanager/rest/reports/1/", "restricted"),
        ("patch", "/reportmanager/rest/reports/", "normal"),
        ("patch", "/reportmanager/rest/reports/", "restricted"),
        ("patch", "/reportmanager/rest/reports/1/", "restricted"),
        ("post", "/reportmanager/rest/reports/1/", "normal"),
        ("post", "/reportmanager/rest/reports/1/", "restricted"),
        ("put", "/reportmanager/rest/reports/", "normal"),
        ("put", "/reportmanager/rest/reports/", "restricted"),
        ("put", "/reportmanager/rest/reports/1/", "normal"),
        ("put", "/reportmanager/rest/reports/1/", "restricted"),
    ],
    indirect=["user"],
)
def test_rest_reports_methods(api_client, user, method, url):
    """must yield method-not-allowed for unsupported methods"""
    assert (
        getattr(api_client, method)(url, {}).status_code
        == requests.codes["method_not_allowed"]
    )


def _compare_rest_result_to_report(result, report, raw=True):
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
        "reportAddress",
        "triagedOnce",
        "created",
    }
    if raw:
        expected_fields |= {"rawReportData", "rawStderr", "rawStdout"}
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
        obj = report
        for attr in attrs.split("_"):
            if obj is not None:
                obj = getattr(obj, attr)
        if isinstance(obj, datetime):
            obj = obj.isoformat().replace("+00:00", "Z")
        assert value == obj


def _compare_created_data_to_report(
    data, report, report_address=None, short_signature=None
):
    for field in ("rawStdout", "rawStderr", "rawReportData"):
        assert getattr(report, field) == data[field].strip()
    if "testcase" in data:
        assert (
            os.path.splitext(report.testcase.test.path)[1].lstrip(".")
            == data["testcase_ext"]
        )
        with open(report.testcase.test.path) as fp:
            assert fp.read() == data["testcase"]
        assert report.testcase.isBinary == data["testcase_isbinary"]
        assert report.testcase.quality == data["testcase_quality"]
    else:
        assert report.testcase is None
    for field in ("platform", "product", "os", "client", "tool"):
        assert getattr(report, field).name == data[field]
    assert report.product.version == data["product_version"]
    if report_address is not None:
        assert report.reportAddress == report_address
    if short_signature is not None:
        assert report.shortSignature == short_signature


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
@pytest.mark.parametrize("ignore_toolfilter", [True, False])
@pytest.mark.parametrize("include_raw", [True, False])
def test_rest_reports_list(api_client, user, cm, ignore_toolfilter, include_raw):
    """test that list returns the right reports"""
    # if restricted or normal, must only list reports in toolfilter
    buckets = [cm.create_bucket(shortDescription="bucket #1"), None]
    testcases = [
        cm.create_testcase("test3.txt", quality=5),
        cm.create_testcase("test4.txt", quality=5),
    ]
    tools = ["tool2", "tool1"]
    reports = [
        cm.create_report(
            shortSignature="report #%d" % (i + 1),
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
    # Create toolfilter, check that query returns only tool-filtered reports
    cm.create_toolfilter("tool2", user=user.username)
    params = {}
    if ignore_toolfilter:
        params["ignore_toolfilter"] = "1"
    if not include_raw:
        params["include_raw"] = "0"
    resp = api_client.get("/reportmanager/rest/reports/", params)
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
    for result, report in zip(resp["results"], reports[:expected]):
        _compare_rest_result_to_report(result, report, raw=include_raw)


@pytest.mark.parametrize("ignore_toolfilter", [True, False])
def test_rest_reports_delete(api_client, user_normal, cm, ignore_toolfilter, mocker):
    """test that delete reports api works as expected"""
    fake_cache = mocker.patch("redis.StrictRedis.from_url")
    fake_delete_task = mocker.patch("reportmanager.views.bulk_delete_reports")
    testcases = [
        cm.create_testcase("test3.txt", quality=5),
        cm.create_testcase("test4.txt", quality=5),
    ]
    tools = ["tool2", "tool1"]
    for i in range(2):
        cm.create_report(
            shortSignature=f"report #{i + 1}",
            client=f"client #{i + 1}",
            os=f"os #{i + 1}",
            product=f"product #{i + 1}",
            product_version=f"{i + 1}",
            platform=f"platform #{i + 1}",
            tool=tools[i],
            testcase=testcases[i],
        )
    # Create toolfilter, check that delete affects only tool-filtered reports
    cm.create_toolfilter("tool2", user=user_normal.username)
    params = {}
    if ignore_toolfilter:
        params["ignore_toolfilter"] = "1"

    # DRF APIClient only handles URL params for GET
    # for DELETE, have to build them ourselves
    query_string = urlencode(params, doseq=True)

    resp = api_client.delete("/reportmanager/rest/reports/", QUERY_STRING=query_string)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["accepted"]
    token = resp.json()
    assert fake_cache.return_value.sadd.call_args_list == [
        mocker.call("cm_async_operations", token)
    ]
    assert len(fake_delete_task.delay.call_args_list) == 1
    call_args, call_kwds = fake_delete_task.delay.call_args_list[0]
    assert not call_kwds
    assert len(call_args) == 2
    assert call_args[1] == token
    reports = ReportEntry.objects.all()
    reports.query = call_args[0]
    LOG.debug(reports.query)
    if ignore_toolfilter:
        assert (
            reports.count() == 2
        ), f"deleting: {','.join(str(report.id) for report in reports)}"
    else:
        assert (
            reports.count() == 1
        ), f"deleting: {','.join(str(report.id) for report in reports)}"
        entry = reports.get()
        assert entry.tool.name == "tool2"


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
@pytest.mark.parametrize("ignore_toolfilter", [True, False])
@pytest.mark.parametrize("include_raw", [True, False])
def test_rest_reports_retrieve(api_client, user, cm, ignore_toolfilter, include_raw):
    """test that retrieve returns the right report"""
    # if restricted or normal, must only list reports in toolfilter
    buckets = [cm.create_bucket(shortDescription="bucket #1"), None]
    testcases = [
        cm.create_testcase("test3.txt", quality=5),
        cm.create_testcase("test4.txt", quality=5),
    ]
    tools = ["tool2", "tool1"]
    reports = [
        cm.create_report(
            shortSignature="report #%d" % (i + 1),
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
    # Create toolfilter, check that query returns only tool-filtered reports
    cm.create_toolfilter("tool2", user=user.username)
    params = {}
    if ignore_toolfilter:
        params["ignore_toolfilter"] = "1"
    if not include_raw:
        params["include_raw"] = "0"
    for i, report in enumerate(reports):
        resp = api_client.get("/reportmanager/rest/reports/%d/" % report.pk, params)
        LOG.debug(resp)
        allowed = user.username == "test" or tools[i] == "tool2"
        if not allowed:
            assert resp.status_code == requests.codes["not_found"]
        else:
            status_code = resp.status_code
            resp = resp.json()
            assert status_code == requests.codes["ok"], resp["detail"]
            _compare_rest_result_to_report(resp, report, raw=include_raw)


@pytest.mark.parametrize(
    "user, expected, toolfilter",
    [
        ("normal", 3, None),
        ("restricted", None, None),
        ("restricted", 3, "tool1"),
    ],
    indirect=["user"],
)
def test_rest_reports_list_query(api_client, cm, user, expected, toolfilter):
    """test that reports can be queried"""
    buckets = [cm.create_bucket(shortDescription="bucket #1"), None, None, None]
    testcases = [
        cm.create_testcase("test1.txt", quality=5),
        cm.create_testcase("test2.txt", quality=0),
        cm.create_testcase("test3.txt", quality=5),
        cm.create_testcase("test4.txt", quality=5),
    ]
    tools = ["tool1", "tool1", "tool2", "tool1"]
    reports = [
        cm.create_report(
            shortSignature="report #%d" % (i + 1),
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
        "/reportmanager/rest/reports/",
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
        _compare_rest_result_to_report(resp["results"][0], reports[expected])


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
@pytest.mark.parametrize(
    "data",
    [
        # simple create
        {
            "rawStdout": "data on\nstdout",
            "rawStderr": "data on\nstderr",
            "rawReportData": "some\treport\ndata\n",
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
        # report reporting works with no testcase
        {
            "rawStdout": "data on\nstdout",
            "rawStderr": "data on\nstderr",
            "rawReportData": "some\nreport\ndata",
            "platform": "x86",
            "product": "mozilla-central",
            "product_version": "badf00d",
            "os": "linux",
            "client": "client1",
            "tool": "tool1",
            "testcase_ext": "js",
        },
        # report reporting works with empty fields where allowed
        {
            "rawStdout": "",
            "rawStderr": "",
            "rawReportData": "",
            "testcase": "blah",
            "testcase_isbinary": False,
            "testcase_quality": 0,
            "testcase_ext": "",
            "platform": "x",
            "product": "x",
            "product_version": "",
            "os": "x",
            "client": "x",
            "tool": "x",
        },
    ],
)
def test_rest_reports_report_report(api_client, user, data):
    """test that report reporting works"""
    resp = api_client.post("/reportmanager/rest/reports/", data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["created"]
    report = ReportEntry.objects.get()
    _compare_created_data_to_report(data, report)


def test_rest_reports_report_report_long(api_client, user_normal):
    """test that report reporting works with fields interpreted as `long` in python 2"""
    data = {
        "rawStdout": "",
        "rawStderr": "",
        "rawReportData": (FIXTURE_PATH / "gdb_report_data.txt").read_text(),
        "testcase": "blah",
        "testcase_isbinary": False,
        "testcase_quality": 0,
        "testcase_ext": "",
        "platform": "x86_64",
        "product": "x",
        "product_version": "",
        "os": "linux",
        "client": "x",
        "tool": "x",
    }
    resp = api_client.post("/reportmanager/rest/reports/", data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["created"]
    report = ReportEntry.objects.get()
    _compare_created_data_to_report(data, report, report_address="0xf7056fff")


@patch(
    "reportmanager.models.ReportEntry.save",
    new=Mock(side_effect=RuntimeError("reportentry failing intentionally")),
)
def test_rest_reports_report_bad_report_removes_testcase(api_client, user_normal):
    """test that reporting a bad report doesn't leave an orphaned testcase"""
    data = {
        "rawStdout": "data on\nstdout",
        "rawStderr": "data on\nstderr",
        "rawReportData": "some\treport\ndata\n",
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
        api_client.post("/reportmanager/rest/reports/", data=data)
    assert not ReportEntry.objects.exists()
    assert not cmTestCase.objects.exists()


def test_rest_reports_report_report_long_sig(api_client, user_normal):
    """test that report reporting works with an assertion message too long for
    shortSignature"""
    data = {
        "rawStdout": "data on\nstdout",
        "rawStderr": "data on\nstderr",
        "rawReportData": "Assertion failure: " + ("A" * 4096),
        "platform": "x86",
        "product": "mozilla-central",
        "product_version": "badf00d",
        "os": "linux",
        "client": "client1",
        "tool": "tool1",
    }
    resp = api_client.post("/reportmanager/rest/reports/", data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes["created"]
    report = ReportEntry.objects.get()
    expected = ("Assertion failure: " + ("A" * 4096))[
        : ReportEntry._meta.get_field("shortSignature").max_length
    ]
    _compare_created_data_to_report(data, report, short_signature=expected)


def test_rest_report_update(api_client, cm, user_normal):
    """test that only allowed fields of ReportEntry can be updated"""
    test = cm.create_testcase("test.txt", quality=0)
    bucket = cm.create_bucket(shortDescription="bucket #1")
    report = cm.create_report(
        shortSignature="report #1",
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
        "rawReportData",
        "rawStderr",
        "rawStdout",
        "testcase",
        "testcase_isbinary",
        "tool",
        "shortSignature",
        "reportAddress",
    }
    for field in fields:
        resp = api_client.patch(
            "/reportmanager/rest/reports/%d/" % report.pk, {field: ""}
        )
        LOG.debug(resp)
        assert resp.status_code == requests.codes["bad_request"]
    resp = api_client.patch(
        "/reportmanager/rest/reports/%d/" % report.pk, {"testcase_quality": "5"}
    )
    LOG.debug(resp)
    assert resp.status_code == requests.codes["ok"]
    test = cmTestCase.objects.get(pk=test.pk)  # re-read
    assert test.quality == 5


def test_rest_report_update_restricted(api_client, cm, user_restricted):
    """test that restricted users cannot perform updates on ReportEntry"""
    test = cm.create_testcase("test.txt", quality=0)
    bucket = cm.create_bucket(shortDescription="bucket #1")
    report = cm.create_report(
        shortSignature="report #1",
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
        "rawReportData",
        "rawStderr",
        "rawStdout",
        "testcase",
        "testcase_isbinary",
        "testcase_quality",
        "tool",
        "shortSignature",
        "reportAddress",
    }
    for field in fields:
        resp = api_client.patch(
            "/reportmanager/rest/reports/%d/" % report.pk, {field: ""}
        )
        LOG.debug(resp)
        assert resp.status_code == requests.codes["method_not_allowed"]
