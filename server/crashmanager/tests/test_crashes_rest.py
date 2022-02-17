# coding: utf-8
'''Tests for Crashes rest api.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
from __future__ import unicode_literals
from datetime import datetime
import json
import logging
import os.path
import pytest
import requests
from crashmanager.models import CrashEntry, TestCase as cmTestCase

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


# What should be allowed:
#
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# |        |      |          | no auth | no perm | unrestricted | unrestricted,     | restricted | restricted,       |
# |        |      |          |         |         |              | ignore_toolfilter |            | ignore_toolfilter |
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# | GET    | /    | list     | 401     | 403     | toolfilter   | all               | toolfilter | toolfilter        |
# |        +------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# |        | /id/ | retrieve | 401     | 403     | all          | all               | toolfilter | toolfilter        |
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# | POST   | /    | create   | 401     | 403     | all          | all               | all        | all               |
# |        +------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# |        | /id/ | -        | 401     | 403     | 405          | 405               | 405        | 405               |
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# | PUT    | /    | -        | 401     | 403     | 405          | 405               | 405        | 405               |
# |        +------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# |        | /id/ | -        | 401     | 403     | 405          | 405               | 405        | 405               |
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# | PATCH  | /    | -        | 401     | 403     | 405          | 405               | 405        | 405               |
# |        +------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# |        | /id/ | update   | 401     | 403     | all          | all               | 405        | 405               |
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# | DELETE | /    | -        | 401     | 403     | 405          | 405               | 405        | 405               |
# |        +------+----------+---------+---------+--------------+-------------------+------------+-------------------+
# |        | /id/ | delete   | 401     | 403     | all (TODO)   | all (TODO)        | 405        | 405               |
# +--------+------+----------+---------+---------+--------------+-------------------+------------+-------------------+


LOG = logging.getLogger("fm.crashmanager.tests.crashes.rest")


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
@pytest.mark.parametrize("url", ["/crashmanager/rest/crashes/", "/crashmanager/rest/crashes/1/"])
def test_rest_crashes_no_auth(db, api_client, method, url):
    """must yield unauthorized without authentication"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes['unauthorized']


@pytest.mark.parametrize("method", ["delete", "get", "patch", "post", "put"])
@pytest.mark.parametrize("url", ["/crashmanager/rest/crashes/", "/crashmanager/rest/crashes/1/"])
def test_rest_crashes_no_perm(user_noperm, api_client, method, url):
    """must yield forbidden without permission"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes['forbidden']


@pytest.mark.parametrize("method, url, user", [
    ("delete", "/crashmanager/rest/crashes/", "normal"),
    ("delete", "/crashmanager/rest/crashes/", "restricted"),
    ("delete", "/crashmanager/rest/crashes/1/", "normal"),  # TODO: this should be allowed, but hasn't been implemented
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
], indirect=["user"])
def test_rest_crashes_methods(api_client, user, method, url):
    """must yield method-not-allowed for unsupported methods"""
    assert getattr(api_client, method)(url, {}).status_code == requests.codes['method_not_allowed']


def _compare_rest_result_to_crash(result, crash, raw=True):
    expected_fields = {
        'args', 'bucket', 'client', 'env', 'id', 'metadata', 'os', 'platform',
        'product', 'product_version',
        'testcase', 'testcase_isbinary', 'testcase_quality', 'testcase_size', 'tool',
        'shortSignature', 'crashAddress', 'triagedOnce', 'created',
    }
    if raw:
        expected_fields |= {'rawCrashData', 'rawStderr', 'rawStdout'}
    assert set(result) == expected_fields
    for key, value in result.items():
        if key == "testcase":
            continue
        attrs = {"client": "client_name",
                 "bucket": "bucket_pk",
                 "os": "os_name",
                 "platform": "platform_name",
                 "product": "product_name",
                 "testcase_isbinary": "testcase_isBinary",
                 "tool": "tool_name"}.get(key, key)
        obj = crash
        for attr in attrs.split("_"):
            if obj is not None:
                obj = getattr(obj, attr)
        if isinstance(obj, datetime):
            obj = obj.isoformat().replace("+00:00", "Z")
        assert value == obj


def _compare_created_data_to_crash(data, crash, crash_address=None, short_signature=None):
    for field in ('rawStdout', 'rawStderr', 'rawCrashData'):
        assert getattr(crash, field) == data[field].strip()
    if 'testcase' in data:
        assert os.path.splitext(crash.testcase.test.path)[1].lstrip('.') == data['testcase_ext']
        with open(crash.testcase.test.path) as fp:
            assert fp.read() == data['testcase']
        assert crash.testcase.isBinary == data['testcase_isbinary']
        assert crash.testcase.quality == data['testcase_quality']
    else:
        assert crash.testcase is None
    for field in ('platform', 'product', 'os', 'client', 'tool'):
        assert getattr(crash, field).name == data[field]
    assert crash.product.version == data['product_version']
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
    testcases = [cm.create_testcase("test3.txt", quality=5),
                 cm.create_testcase("test4.txt", quality=5)]
    tools = ["tool2", "tool1"]
    crashes = [cm.create_crash(shortSignature="crash #%d" % (i + 1),
                               client="client #%d" % (i + 1),
                               os="os #%d" % (i + 1),
                               product="product #%d" % (i + 1),
                               product_version="%d" % (i + 1),
                               platform="platform #%d" % (i + 1),
                               tool=tools[i],
                               bucket=buckets[i],
                               testcase=testcases[i])
               for i in range(2)]
    # Create toolfilter, check that query returns only tool-filtered crashes
    cm.create_toolfilter('tool2', user=user.username)
    params = {}
    if ignore_toolfilter:
        params["ignore_toolfilter"] = "1"
    if not include_raw:
        params["include_raw"] = "0"
    resp = api_client.get("/crashmanager/rest/crashes/", params)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    expected = 2 if ignore_toolfilter and user.username == "test" else 1
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp) == {'count', 'next', 'previous', 'results'}
    assert resp['count'] == expected
    assert resp['next'] is None
    assert resp['previous'] is None
    assert len(resp['results']) == expected
    for result, crash in zip(resp['results'], crashes[:expected]):
        _compare_rest_result_to_crash(result, crash, raw=include_raw)


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
@pytest.mark.parametrize("ignore_toolfilter", [True, False])
@pytest.mark.parametrize("include_raw", [True, False])
def test_rest_crashes_retrieve(api_client, user, cm, ignore_toolfilter, include_raw):
    """test that retrieve returns the right crash"""
    # if restricted or normal, must only list crashes in toolfilter
    buckets = [cm.create_bucket(shortDescription="bucket #1"), None]
    testcases = [cm.create_testcase("test3.txt", quality=5),
                 cm.create_testcase("test4.txt", quality=5)]
    tools = ["tool2", "tool1"]
    crashes = [cm.create_crash(shortSignature="crash #%d" % (i + 1),
                               client="client #%d" % (i + 1),
                               os="os #%d" % (i + 1),
                               product="product #%d" % (i + 1),
                               product_version="%d" % (i + 1),
                               platform="platform #%d" % (i + 1),
                               tool=tools[i],
                               bucket=buckets[i],
                               testcase=testcases[i])
               for i in range(2)]
    # Create toolfilter, check that query returns only tool-filtered crashes
    cm.create_toolfilter('tool2', user=user.username)
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
            assert resp.status_code == requests.codes['not_found']
        else:
            status_code = resp.status_code
            resp = resp.json()
            assert status_code == requests.codes['ok'], resp['detail']
            _compare_rest_result_to_crash(resp, crash, raw=include_raw)


@pytest.mark.parametrize("user, expected, toolfilter", [
    ("normal", 3, None),
    ("restricted", None, None),
    ("restricted", 3, "tool1"),
], indirect=["user"])
def test_rest_crashes_list_query(api_client, cm, user, expected, toolfilter):
    """test that crashes can be queried"""
    buckets = [cm.create_bucket(shortDescription="bucket #1"), None, None, None]
    testcases = [cm.create_testcase("test1.txt", quality=5),
                 cm.create_testcase("test2.txt", quality=0),
                 cm.create_testcase("test3.txt", quality=5),
                 cm.create_testcase("test4.txt", quality=5)]
    tools = ["tool1", "tool1", "tool2", "tool1"]
    crashes = [cm.create_crash(shortSignature="crash #%d" % (i + 1),
                               client="client #%d" % (i + 1),
                               os="os #%d" % (i + 1),
                               product="product #%d" % (i + 1),
                               product_version="%d" % (i + 1),
                               platform="platform #%d" % (i + 1),
                               tool=tools[i],
                               bucket=buckets[i],
                               testcase=testcases[i])
               for i in range(4)]
    if toolfilter is not None:
        cm.create_toolfilter(toolfilter, user=user.username)
    resp = api_client.get('/crashmanager/rest/crashes/',
                          {"query": json.dumps({"op": "AND",
                                                "bucket": None,
                                                "testcase__quality": 5,
                                                "tool__name__in": ["tool1"]})})
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp) == {'count', 'next', 'previous', 'results'}
    assert resp['count'] == (0 if expected is None else 1)
    assert resp['next'] is None
    assert resp['previous'] is None
    assert len(resp['results']) == resp['count']
    if expected is not None:
        _compare_rest_result_to_crash(resp['results'][0], crashes[expected])


@pytest.mark.parametrize("user", ["normal", "restricted"], indirect=True)
@pytest.mark.parametrize("data", [
    # simple create
    {
        'rawStdout': 'data on\nstdout',
        'rawStderr': 'data on\nstderr',
        'rawCrashData': 'some\tcrash\ndata\n',
        'testcase': 'foo();\ntest();',
        'testcase_isbinary': False,
        'testcase_quality': 0,
        'testcase_ext': 'js',
        'platform': 'x86',
        'product': 'mozilla-central',
        'product_version': 'badf00d',
        'os': 'linux',
        'client': 'client1',
        'tool': 'tool1',
    },
    # crash reporting works with no testcase
    {
        'rawStdout': 'data on\nstdout',
        'rawStderr': 'data on\nstderr',
        'rawCrashData': 'some\ncrash\ndata',
        'platform': 'x86',
        'product': 'mozilla-central',
        'product_version': 'badf00d',
        'os': 'linux',
        'client': 'client1',
        'tool': 'tool1',
        'testcase_ext': 'js',
    },
    # crash reporting works with empty fields where allowed
    {
        'rawStdout': '',
        'rawStderr': '',
        'rawCrashData': '',
        'testcase': 'blah',
        'testcase_isbinary': False,
        'testcase_quality': 0,
        'testcase_ext': '',
        'platform': 'x',
        'product': 'x',
        'product_version': '',
        'os': 'x',
        'client': 'x',
        'tool': 'x',
    },
])
def test_rest_crashes_report_crash(api_client, user, data):
    """test that crash reporting works"""
    resp = api_client.post('/crashmanager/rest/crashes/', data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['created']
    crash = CrashEntry.objects.get()
    _compare_created_data_to_crash(data, crash)


def test_rest_crashes_report_crash_long(api_client, user_normal):
    """test that crash reporting works with fields interpreted as `long` in python 2"""
    data = {
        'rawStdout': '',
        'rawStderr': '',
        'rawCrashData': r'''GNU gdb (Ubuntu 7.11.1-0ubuntu1~16.5) 7.11.1
(gdb) backtrace 0
No stack.
(gdb) r
Starting program: /home/ubuntu/shell-cache/js-32-linux-dc70d241f90d/js-32-linux-dc70d241f90d --fuzzing-safe --no-threads --ion-eager bb2608227.js
Thread 1 "js-32-linux-dc7" received signal SIGSEGV, Segmentation fault.
0x33674039 in ?? ()
(gdb) backtrace
#0  0x33674039 in ?? ()
#1  0xf6b52820 in ?? ()
#2  0xf6b52820 in ?? ()
(gdb) info registers
eax            0xf7047000	-150704128
ecx            0xffef	65519
edx            0xffff8000	-32768
ebx            0x9837ff4	159612916
esp            0xffffba74	0xffffba74
ebp            0xffffba74	0xffffba74
esi            0xf6b52820	-155899872
edi            0xf6f896c0	-151480640
eip            0x33674039	0x33674039
eflags         0x10283	[ CF SF IF RF ]
cs             0x23	35
ss             0x2b	43
ds             0x2b	43
es             0x2b	43
fs             0x0	0
gs             0x63	99
(gdb) print $_siginfo
$1 = {si_signo = 11, si_errno = 0, si_code = 2, _sigfault = {si_addr = 0xf7057000, _addr_lsb = 0, _addr_bnd = {_lower = 0x0, _upper = 0x0}}}
(gdb) x/8i $pc
=> 0x33674039:	mov    %dx,0x10(%eax,%ecx,1)
   0x3367403e:	pop    %ebp
   0x3367403f:	pop    %esi
   0x33674040:	ret
   0x33674041:	jmp    0x33674200
   0x33674046:	sub    $0x4,%esp
   0x33674049:	call   0x336743f0
   0x3367404e:	sub    $0x4,%esp
''',  # noqa
        'testcase': 'blah',
        'testcase_isbinary': False,
        'testcase_quality': 0,
        'testcase_ext': '',
        'platform': 'x86_64',
        'product': 'x',
        'product_version': '',
        'os': 'linux',
        'client': 'x',
        'tool': 'x'}
    resp = api_client.post('/crashmanager/rest/crashes/', data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['created']
    crash = CrashEntry.objects.get()
    _compare_created_data_to_crash(data, crash, crash_address='0xf7056fff')


@patch('crashmanager.models.CrashEntry.save', new=Mock(side_effect=RuntimeError("crashentry failing intentionally")))
def test_rest_crashes_report_bad_crash_removes_testcase(api_client, user_normal):
    """test that reporting a bad crash doesn't leave an orphaned testcase"""
    data = {
        'rawStdout': 'data on\nstdout',
        'rawStderr': 'data on\nstderr',
        'rawCrashData': 'some\tcrash\ndata\n',
        'testcase': 'foo();\ntest();',
        'testcase_isbinary': False,
        'testcase_quality': 0,
        'testcase_ext': 'js',
        'platform': 'x86',
        'product': 'mozilla-central',
        'product_version': 'badf00d',
        'os': 'linux',
        'client': 'client1',
        'tool': 'tool1'}
    with pytest.raises(RuntimeError):
        api_client.post('/crashmanager/rest/crashes/', data=data)
    assert not CrashEntry.objects.exists()
    assert not cmTestCase.objects.exists()


def test_rest_crashes_report_crash_long_sig(api_client, user_normal):
    """test that crash reporting works with an assertion message too long for shortSignature"""
    data = {
        'rawStdout': 'data on\nstdout',
        'rawStderr': 'data on\nstderr',
        'rawCrashData': 'Assertion failure: ' + ('A' * 4096),
        'platform': 'x86',
        'product': 'mozilla-central',
        'product_version': 'badf00d',
        'os': 'linux',
        'client': 'client1',
        'tool': 'tool1'}
    resp = api_client.post('/crashmanager/rest/crashes/', data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['created']
    crash = CrashEntry.objects.get()
    expected = ('Assertion failure: ' + ('A' * 4096))[:CrashEntry._meta.get_field('shortSignature').max_length]
    _compare_created_data_to_crash(data, crash, short_signature=expected)


def test_rest_crash_update(api_client, cm, user_normal):
    """test that only allowed fields of CrashEntry can be updated"""
    test = cm.create_testcase("test.txt", quality=0)
    bucket = cm.create_bucket(shortDescription="bucket #1")
    crash = cm.create_crash(shortSignature="crash #1",
                            bucket=bucket,
                            client="client #1",
                            os="os #1",
                            product="product #1",
                            product_version="1",
                            platform="platform #1",
                            tool="tool #1",
                            testcase=test)
    fields = {'args', 'bucket', 'client', 'env', 'id', 'metadata', 'os', 'platform', 'product', 'product_version',
              'rawCrashData', 'rawStderr', 'rawStdout', 'testcase', 'testcase_isbinary', 'tool',
              'shortSignature', 'crashAddress'}
    for field in fields:
        resp = api_client.patch('/crashmanager/rest/crashes/%d/' % crash.pk, {field: ""})
        LOG.debug(resp)
        assert resp.status_code == requests.codes['bad_request']
    resp = api_client.patch('/crashmanager/rest/crashes/%d/' % crash.pk, {"testcase_quality": "5"})
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    test = cmTestCase.objects.get(pk=test.pk)  # re-read
    assert test.quality == 5


def test_rest_crash_update_restricted(api_client, cm, user_restricted):
    """test that restricted users cannot perform updates on CrashEntry"""
    test = cm.create_testcase("test.txt", quality=0)
    bucket = cm.create_bucket(shortDescription="bucket #1")
    crash = cm.create_crash(shortSignature="crash #1",
                            bucket=bucket,
                            client="client #1",
                            os="os #1",
                            product="product #1",
                            product_version="1",
                            platform="platform #1",
                            tool="tool #1",
                            testcase=test)
    fields = {'args', 'bucket', 'client', 'env', 'id', 'metadata', 'os', 'platform', 'product', 'product_version',
              'rawCrashData', 'rawStderr', 'rawStdout', 'testcase', 'testcase_isbinary', 'testcase_quality', 'tool',
              'shortSignature', 'crashAddress'}
    for field in fields:
        resp = api_client.patch('/crashmanager/rest/crashes/%d/' % crash.pk, {field: ""})
        LOG.debug(resp)
        assert resp.status_code == requests.codes['method_not_allowed']
