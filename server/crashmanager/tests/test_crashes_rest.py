# coding: utf-8
'''Tests for Crashes rest api.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
from __future__ import unicode_literals
import json
import logging
import os.path
import pytest
import requests
from django.contrib.auth.models import User
from crashmanager.models import CrashEntry, TestCase as cmTestCase

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


LOG = logging.getLogger("fm.crashmanager.tests.crashes.rest")
pytestmark = pytest.mark.usefixtures("crashmanager_test")  # pylint: disable=invalid-name


def test_rest_crashes_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = '/crashmanager/rest/crashes/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.put(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.patch(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.delete(url, {}).status_code == requests.codes['unauthorized']


def test_rest_crashes_no_perm(api_client):
    """must yield forbidden without permission"""
    url = '/crashmanager/rest/crashes/'
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url, {}).status_code == requests.codes['forbidden']
    assert api_client.put(url, {}).status_code == requests.codes['forbidden']
    assert api_client.patch(url, {}).status_code == requests.codes['forbidden']
    assert api_client.delete(url, {}).status_code == requests.codes['forbidden']


def test_rest_crashes_auth(api_client):
    """test that authenticated requests work"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/crashmanager/rest/crashes/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']


def test_rest_crashes_patch(api_client):
    """patch should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.patch('/crashmanager/rest/crashes/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_crashes_put(api_client):
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/crashmanager/rest/crashes/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_crashes_delete(api_client):
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/crashmanager/rest/crashes/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_crashes_report_crash(api_client):
    """test that crash reporting works"""
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
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/crashmanager/rest/crashes/', data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['created']
    crash = CrashEntry.objects.get()
    for field in ('rawStdout', 'rawStderr', 'rawCrashData'):
        assert getattr(crash, field) == data[field].strip()
    assert os.path.splitext(crash.testcase.test.path)[1].lstrip('.') == data['testcase_ext']
    with open(crash.testcase.test.path) as fp:
        assert fp.read() == data['testcase']
    assert crash.testcase.isBinary == data['testcase_isbinary']
    assert crash.testcase.quality == data['testcase_quality']
    for field in ('platform', 'product', 'os', 'client', 'tool'):
        assert getattr(crash, field).name == data[field]
    assert crash.product.version == data['product_version']


def test_rest_crashes_report_crash_no_test(api_client):
    """test that crash reporting works with no testcase"""
    data = {
        'rawStdout': 'data on\nstdout',
        'rawStderr': 'data on\nstderr',
        'rawCrashData': 'some\ncrash\ndata',
        'platform': 'x86',
        'product': 'mozilla-central',
        'product_version': 'badf00d',
        'os': 'linux',
        'client': 'client1',
        'tool': 'tool1'}
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/crashmanager/rest/crashes/', data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['created']
    crash = CrashEntry.objects.get()
    for field in ('rawStdout', 'rawStderr', 'rawCrashData'):
        assert getattr(crash, field) == data[field]
    assert crash.testcase is None
    for field in ('platform', 'product', 'os', 'client', 'tool'):
        assert getattr(crash, field).name == data[field]
    assert crash.product.version == data['product_version']


def test_rest_crashes_report_crash_empty(api_client):
    """test that crash reporting works with empty fields where allowed"""
    data = {
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
        'tool': 'x'}
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/crashmanager/rest/crashes/', data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['created']
    crash = CrashEntry.objects.get()
    for field in ('rawStdout', 'rawStderr', 'rawCrashData'):
        assert getattr(crash, field) == data[field]
    assert os.path.splitext(crash.testcase.test.path)[1].lstrip('.') == data['testcase_ext']
    with open(crash.testcase.test.path) as fp:
        assert fp.read() == data['testcase']
    assert crash.testcase.isBinary == data['testcase_isbinary']
    assert crash.testcase.quality == data['testcase_quality']
    for field in ('platform', 'product', 'os', 'client', 'tool'):
        assert getattr(crash, field).name == data[field]
    assert crash.product.version == data['product_version']


def test_rest_crashes_report_crash_long(api_client):
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
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/crashmanager/rest/crashes/', data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['created']
    crash = CrashEntry.objects.get()
    for field in ('rawStdout', 'rawStderr', 'rawCrashData'):
        assert getattr(crash, field) == data[field].strip()
    assert os.path.splitext(crash.testcase.test.path)[1].lstrip('.') == data['testcase_ext']
    with open(crash.testcase.test.path) as fp:
        assert fp.read() == data['testcase']
    assert crash.testcase.isBinary == data['testcase_isbinary']
    assert crash.testcase.quality == data['testcase_quality']
    for field in ('platform', 'product', 'os', 'client', 'tool'):
        assert getattr(crash, field).name == data[field]
    assert crash.product.version == data['product_version']
    assert crash.crashAddress == '0xf7056fff'


def test_rest_crashes_query_crash(api_client, cm):
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
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/crashmanager/rest/crashes/',
                          {"query": json.dumps({"op": "AND",
                                                "bucket": None,
                                                "testcase__quality": 5,
                                                "tool__name__in": ["tool1"]})})
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()) == {'count', 'next', 'previous', 'results'}
    assert resp['count'] == 1
    assert resp['next'] is None
    assert resp['previous'] is None
    assert len(resp['results']) == 1
    resp = resp['results'][0]
    assert set(resp.keys()) == {
        'args', 'bucket', 'client', 'env', 'id', 'metadata', 'os', 'platform',
        'product', 'product_version', 'rawCrashData', 'rawStderr', 'rawStdout',
        'testcase', 'testcase_isbinary', 'testcase_quality', 'testcase_size', 'tool',
        'shortSignature', 'crashAddress',
    }
    for key, value in resp.items():
        if key == "testcase":
            continue
        attrs = {"client": "client_name",
                 "os": "os_name",
                 "platform": "platform_name",
                 "product": "product_name",
                 "testcase_isbinary": "testcase_isBinary",
                 "tool": "tool_name"}.get(key, key)
        result = crashes[3]
        for attr in attrs.split("_"):
            result = getattr(result, attr)
        assert value == result

    # Repeat the same with a restricted user, check that query returns 403
    user = User.objects.get(username='test-restricted')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/crashmanager/rest/crashes/',
                          {"query": json.dumps({"op": "AND",
                                                "bucket": None,
                                                "testcase__quality": 5,
                                                "tool__name__in": ["tool1"]})})
    LOG.debug(resp)
    assert resp.status_code == requests.codes['forbidden']


def test_rest_crashes_list_noraw(api_client, cm):
    """test that crashes can be listed without raw fields"""
    testcase = cm.create_testcase("test1.txt", quality=5)
    crash = cm.create_crash(shortSignature="crash #1",
                            client="client #1",
                            os="os #1",
                            product="product #1",
                            product_version="1",
                            platform="platform #1",
                            tool="tool1",
                            bucket=None,
                            testcase=testcase)
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/crashmanager/rest/crashes/', {'include_raw': '0'})
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()) == {'count', 'next', 'previous', 'results'}
    assert resp['count'] == 1
    assert resp['next'] is None
    assert resp['previous'] is None
    assert len(resp['results']) == 1
    resp = resp['results'][0]
    assert set(resp.keys()) == {
        'args', 'bucket', 'client', 'env', 'id', 'metadata', 'os', 'platform',
        'product', 'product_version', 'testcase', 'testcase_isbinary',
        'testcase_quality', 'testcase_size', 'tool', 'shortSignature', 'crashAddress',
    }
    for key, value in resp.items():
        if key == "testcase":
            continue
        attrs = {"client": "client_name",
                 "os": "os_name",
                 "platform": "platform_name",
                 "product": "product_name",
                 "testcase_isbinary": "testcase_isBinary",
                 "tool": "tool_name"}.get(key, key)
        result = crash
        for attr in attrs.split("_"):
            result = getattr(result, attr)
        assert value == result


def test_rest_crash_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = '/crashmanager/rest/crashes/1/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.put(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.patch(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.delete(url, {}).status_code == requests.codes['unauthorized']


def test_rest_crash_no_perm(api_client):
    """must yield forbidden without permission"""
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    url = '/crashmanager/rest/crashes/1/'
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url, {}).status_code, requests.codes['forbidden']
    assert api_client.put(url, {}).status_code, requests.codes['forbidden']
    assert api_client.patch(url, {}).status_code, requests.codes['forbidden']
    assert api_client.delete(url, {}).status_code, requests.codes['forbidden']


def test_rest_crash_auth(api_client):
    """test that authenticated requests work"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/crashmanager/rest/crashes/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']


def test_rest_crash_restricted(api_client):
    """test that restricted users are rejected"""
    user = User.objects.get(username='test-restricted')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/crashmanager/rest/crashes/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['forbidden']


def test_rest_crash_delete(api_client):
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/crashmanager/rest/crashes/1/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_crash_put(api_client):
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/crashmanager/rest/crashes/1/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_crash_post(api_client):
    """post should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/crashmanager/rest/crashes/1/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_crash_get(api_client, cm):
    """test that individual CrashEntry can be fetched"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
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
    resp = api_client.get('/crashmanager/rest/crashes/%d/' % crash.pk)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()) == {
        'args', 'bucket', 'client', 'env', 'id', 'metadata', 'os', 'platform',
        'product', 'product_version', 'rawCrashData', 'rawStderr', 'rawStdout',
        'testcase', 'testcase_isbinary', 'testcase_size', 'testcase_quality', 'tool',
        'shortSignature', 'crashAddress',
    }
    for key, value in resp.items():
        if key == "testcase":
            continue
        attrs = {"client": "client_name",
                 "os": "os_name",
                 "bucket": "bucket_pk",
                 "platform": "platform_name",
                 "product": "product_name",
                 "testcase_isbinary": "testcase_isBinary",
                 "tool": "tool_name"}.get(key, key)
        result = crash
        for attr in attrs.split("_"):
            result = getattr(result, attr)
        assert value == result


def test_rest_crash_get_restricted(api_client, cm):
    """test that individual CrashEntry can be created but not fetched by restricted user"""
    user = User.objects.get(username='test-restricted')
    api_client.force_authenticate(user=user)
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
    resp = api_client.get('/crashmanager/rest/crashes/%d/' % crash.pk)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['forbidden']

    # Retry with unrestricted user and check that the entry has been created
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/crashmanager/rest/crashes/%d/' % crash.pk)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']


def test_rest_crash_update(api_client, cm):
    """test that only allowed fields of CrashEntry can be updated"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
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


def test_rest_crash_update_restricted(api_client, cm):
    """test that restricted users cannot perform updates on CrashEntry"""
    user = User.objects.get(username='test-restricted')
    api_client.force_authenticate(user=user)
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
        assert resp.status_code == requests.codes['forbidden']


@patch('crashmanager.models.CrashEntry.save', new=Mock(side_effect=RuntimeError("crashentry failing intentionally")))
def test_rest_crashes_report_bad_crash_removes_testcase(api_client):
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
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    with pytest.raises(RuntimeError):
        api_client.post('/crashmanager/rest/crashes/', data=data)
    assert not CrashEntry.objects.exists()
    assert not cmTestCase.objects.exists()


def test_rest_crashes_report_crash_long_sig(api_client):
    """test that crash reporting works with no testcase"""
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
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/crashmanager/rest/crashes/', data=data)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['created']
    crash = CrashEntry.objects.get()
    for field in ('rawStdout', 'rawStderr', 'rawCrashData'):
        assert getattr(crash, field) == data[field]
    assert crash.testcase is None
    expected = ('Assertion failure: ' + ('A' * 4096))[:CrashEntry._meta.get_field('shortSignature').max_length]
    assert crash.shortSignature == expected
