# coding: utf-8
'''Tests for Crashes view.

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
from django.urls import reverse
from crashmanager.models import CrashEntry
from . import assert_contains, assert_not_contains


LOG = logging.getLogger("fm.crashmanager.tests.crashes")
CRASHES_VIEW_FMT = "There are %d unbucketed entries in the database."
ALL_CRASHES_VIEW_FMT = "Displaying all %d entries in database."
pytestmark = pytest.mark.usefixtures("crashmanager_test")  # pylint: disable=invalid-name


# pylint: disable=no-self-use
@pytest.mark.parametrize(("name", "entries_fmt"),
                         [("crashmanager:crashes", CRASHES_VIEW_FMT),
                          ("crashmanager:allcrashes", ALL_CRASHES_VIEW_FMT)])
class TestCrashesViews(object):
    """Common crashes tests"""

    def test_no_crashes(self, client, cm, name, entries_fmt):  # pylint: disable=invalid-name
        """If no crashes in db, an appropriate message is shown."""
        client.login(username='test', password='test')
        response = client.get(reverse(name))
        LOG.debug(response)
        assert response.status_code == requests.codes['ok']
        crashlist = response.context['crashlist']
        assert not crashlist  # 0 crashes
        assert crashlist.number == 1  # 1st page
        assert crashlist.paginator.num_pages == 1  # 1 page total
        assert_contains(response, entries_fmt % 0)

    def test_with_crash(self, client, cm, name, entries_fmt):  # pylint: disable=invalid-name
        """Insert one crash and check that it is shown ok."""
        client.login(username='test', password='test')
        crash = cm.create_crash(shortSignature="crash #1")
        response = client.get(reverse(name))
        LOG.debug(response)
        assert response.status_code == requests.codes['ok']
        assert_contains(response, "crash #1")
        crashlist = response.context['crashlist']
        assert len(crashlist) == 1  # 1 crash
        assert crashlist.number == 1  # 1st page
        assert crashlist.paginator.num_pages == 1  # 1 page total
        assert crashlist[0] == crash  # same crash we created
        assert_contains(response, entries_fmt % 1)

    def test_with_crashes(self, client, cm, name, entries_fmt):  # pylint: disable=invalid-name
        """Insert two crashes and check that they are shown ok."""
        client.login(username='test', password='test')
        crash1 = cm.create_crash(shortSignature="crash #1")
        crash2 = cm.create_crash(shortSignature="crash #2")
        response = client.get(reverse(name))
        LOG.debug(response)
        assert response.status_code == requests.codes['ok']
        assert_contains(response, "crash #1")
        assert_contains(response, "crash #2")
        crashlist = response.context['crashlist']
        assert len(crashlist) == 2  # 2 crashes
        assert crashlist.number == 1  # 1st page
        assert crashlist.paginator.num_pages == 1  # 1 page total
        assert set(crashlist) == {crash1, crash2}  # same crashes we created
        assert_contains(response, entries_fmt % 2)

    def test_with_pagination(self, client, cm, name, entries_fmt):  # pylint: disable=invalid-name
        """Insert more than the page limit and check that they are paginated ok."""
        client.login(username='test', password='test')
        crashes = [cm.create_crash(shortSignature="crash #1"),
                   cm.create_crash(shortSignature="crash #2"),
                   cm.create_crash(shortSignature="crash #3")]

        def _check_page(page, exp_page, crash):
            response = client.get(reverse(name), {'page': page, 'page_size': 1})
            LOG.debug(response)
            assert response.status_code == requests.codes['ok']
            assert_contains(response, crash.shortSignature)
            crashlist = response.context['crashlist']
            assert crashlist.number == exp_page  # page num
            assert crashlist.paginator.num_pages == len(crashes)  # n pages total
            assert len(crashlist) == 1  # 1 crash/page
            assert crashlist[0] == crash  # same crash we created
            assert_contains(response, entries_fmt % len(crashes))

        for page, crash in enumerate(reversed(crashes)):
            _check_page(page + 1, page + 1, crash)
        # check invalid page params
        _check_page(len(crashes) + 1, len(crashes), crashes[0])  # out of range will return last page
        _check_page(-1, len(crashes), crashes[0])  # out of range will return last page
        _check_page("blah", 1, crashes[-1])  # non-integer will return first page

    def test_no_unbucketed(self, client, cm, name, entries_fmt):  # pylint: disable=invalid-name
        """Insert one crash and bucket it, and see that no entries are shown."""
        client.login(username='test', password='test')
        bucket = cm.create_bucket(shortDescription="bucket #1")
        cm.create_crash(shortSignature="crash #1", bucket=bucket)
        response = client.get(reverse(name))
        LOG.debug(response)
        assert response.status_code == requests.codes['ok']
        crashlist = response.context['crashlist']
        assert not crashlist  # 0 crashes
        assert crashlist.number == 1  # 1st page
        assert crashlist.paginator.num_pages == 1  # 1 page total
        assert_contains(response, entries_fmt % 0)

    def test_bucketed(self, client, cm, name, entries_fmt):  # pylint: disable=invalid-name
        """Insert two crashes and bucket one, see that unbucketed is shown."""
        client.login(username='test', password='test')
        bucket = cm.create_bucket(shortDescription="bucket #1")
        cm.create_crash(shortSignature="crash #1", bucket=bucket)
        crash = cm.create_crash(shortSignature="crash #2")
        response = client.get(reverse(name))
        LOG.debug(response)
        assert response.status_code == requests.codes['ok']
        crashlist = response.context['crashlist']
        assert len(crashlist) == 1  # 1 crashes
        assert crashlist.number == 1  # 1st page
        assert crashlist.paginator.num_pages == 1  # 1 page total
        assert crashlist[0] == crash  # same crash we created
        assert_contains(response, entries_fmt % 1)

    def test_bucketed_all_param(self, client, cm, name, entries_fmt):  # pylint: disable=invalid-name
        """Check that all param shows bucketed crashes."""
        client.login(username='test', password='test')
        bucket = cm.create_bucket(shortDescription="bucket #1")
        crashes = [cm.create_crash(shortSignature="crash #1", bucket=bucket),
                   cm.create_crash(shortSignature="crash #2", bucket=bucket)]
        response = client.get(reverse(name), {'all': 1})
        LOG.debug(response)
        assert response.status_code == requests.codes['ok']
        crashlist = response.context['crashlist']
        assert len(crashlist) == 2  # 2 crashes
        assert crashlist.number == 1  # 1st page
        assert crashlist.paginator.num_pages == 1  # 1 page total
        assert set(crashlist) == set(crashes)  # same crashes we created
        # XXX: this message is wrong
        assert_contains(response, entries_fmt % 2)

    def test_filters(self, client, cm, name, entries_fmt):  # pylint: disable=invalid-name
        """Check that filter params are respected."""
        client.login(username='test', password='test')
        buckets = [cm.create_bucket(shortDescription="bucket #1"),
                   None]
        testcases = [None,
                     cm.create_testcase("test.txt", quality=3)]
        crashes = [cm.create_crash(shortSignature="crash #%d" % (i + 1),
                                   client="client #%d" % (i + 1),
                                   os="os #%d" % (i + 1),
                                   product="product #%d" % (i + 1),
                                   platform="platform #%d" % (i + 1),
                                   tool="tool #%d" % (i + 1),
                                   bucket=buckets[i],
                                   testcase=testcases[i])
                   for i in range(2)]

        for params, exp_crashes in (({'all': 1, 'bucket': buckets[0].pk}, {crashes[0]}),
                                    ({'client__name': 'client #2'}, {crashes[1]}),
                                    ({'client__name__contains': '#2'}, {crashes[1]}),
                                    ({'client__name__contains': 'client', 'all': 1}, set(crashes)),
                                    ({'os__name': 'os #2'}, {crashes[1]}),
                                    ({'product__name': 'product #2'}, {crashes[1]}),
                                    ({'platform__name': 'platform #2'}, {crashes[1]}),
                                    ({'testcase__quality': 3}, {crashes[1]}),
                                    ({'tool__name': 'tool #2'}, {crashes[1]}),
                                    ({'tool__name__contains': '#2'}, {crashes[1]})):
            LOG.debug('requesting with %r', params)
            LOG.debug('expecting: %r', exp_crashes)
            response = client.get(reverse(name), params)
            LOG.debug(response)
            assert response.status_code == requests.codes['ok']
            crashlist = response.context['crashlist']
            assert len(crashlist) == len(exp_crashes)  # num crashes
            assert crashlist.number == 1  # 1st page
            assert crashlist.paginator.num_pages == 1  # 1 page total
            assert set(crashlist) == exp_crashes  # expected crashes
            # pylint: disable=superfluous-parens
            assert_contains(response, ("Your search matched %d entries in database." % len(exp_crashes)))


@pytest.mark.parametrize(("name", "kwargs"),
                         [("crashmanager:crashes", {}),
                          ("crashmanager:allcrashes", {}),
                          ("crashmanager:autoassign", {}),
                          ("crashmanager:crashdel", {'crashid': 0}),
                          ("crashmanager:crashedit", {'crashid': 0}),
                          ("crashmanager:crashview", {'crashid': 0}),
                          ("crashmanager:querycrashes", {})])
def test_crashes_no_login(client, name, kwargs):
    """Request without login hits the login redirect"""
    path = reverse(name, kwargs=kwargs)
    resp = client.get(path)
    assert resp.status_code == requests.codes['found']
    assert resp.url == '/login/?next=' + path


def test_crashes_toolfilter(client, cm):  # pylint: disable=invalid-name
    """Create a toolfilter and see that it is respected."""
    client.login(username='test', password='test')
    crashes = (cm.create_crash(shortSignature="crash #1", tool="tool #1"),
               cm.create_crash(shortSignature="crash #2", tool="tool #2"))
    cm.create_toolfilter("tool #1")
    response = client.get(reverse("crashmanager:crashes"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, "crash #1")
    crashlist = response.context['crashlist']
    assert len(crashlist) == 1  # 1 crash
    assert crashlist.number == 1  # 1st page
    assert crashlist.paginator.num_pages == 1  # 1 page total
    assert set(crashlist) == {crashes[0]}  # same crashes we created
    assert_contains(response, CRASHES_VIEW_FMT % 1)


def test_all_crashes_toolfilter(client, cm):  # pylint: disable=invalid-name
    """Check that crashes/all/ view disregards toolfilter."""
    client.login(username='test', password='test')
    crashes = (cm.create_crash(shortSignature="crash #1", tool="tool #1"),
               cm.create_crash(shortSignature="crash #2", tool="tool #2"))
    cm.create_toolfilter("tool #1")
    response = client.get(reverse("crashmanager:allcrashes"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, "crash #1")
    assert_contains(response, "crash #2")
    crashlist = response.context['crashlist']
    assert len(crashlist) == 2  # 2 crashes
    assert crashlist.number == 1  # 1st page
    assert crashlist.paginator.num_pages == 1  # 1 page total
    assert set(crashlist) == set(crashes)  # same crashes we created
    assert_contains(response, ALL_CRASHES_VIEW_FMT % 2)


def test_auto_assign_crashes(client, cm):  # pylint: disable=invalid-name
    """Create crashes and a signature that would match it and see that autoassign buckets it"""
    client.login(username='test', password='test')
    crash = cm.create_crash(shortSignature='crash #1', stderr="blah")
    sig = json.dumps({
        'symptoms': [
            {"src": "stderr",
             "type": "output",
             "value": "/^blah/"}
        ]
    })
    bucket = cm.create_bucket(shortDescription='bucket #1', signature=sig)
    crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
    assert crash.bucket is None
    resp = client.get(reverse("crashmanager:autoassign"))
    assert resp.status_code == requests.codes['found']
    assert resp.url == reverse('crashmanager:crashes')
    crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
    assert crash.bucket == bucket


@pytest.mark.parametrize("name",
                         ["crashmanager:crashdel",
                          "crashmanager:crashedit",
                          "crashmanager:crashview"])
def test_crash_simple_get(client, cm, name):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    crash = cm.create_crash()
    response = client.get(reverse(name, kwargs={"crashid": crash.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_query_crashes(client, cm):  # pylint: disable=invalid-name
    """Crash list queries"""
    client.login(username='test', password='test')
    buckets = [cm.create_bucket(shortDescription="bucket #1"), None]
    testcases = [None, cm.create_testcase("test.txt", quality=3)]
    crashes = [cm.create_crash(shortSignature="crash #%d" % (i + 1),
                               client="client #%d" % (i + 1),
                               os="os #%d" % (i + 1),
                               product="product #%d" % (i + 1),
                               platform="platform #%d" % (i + 1),
                               tool="tool #%d" % (i + 1),
                               bucket=buckets[i],
                               testcase=testcases[i])
               for i in range(2)]
    response = client.get(reverse("crashmanager:querycrashes"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, "Search Query")
    assert_not_contains(response, "Invalid query")
    response = client.get(reverse("crashmanager:querycrashes"), {"query": "badjson"})
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, "Invalid query")
    response = client.post(reverse("crashmanager:querycrashes"), {"query": "badjson"})
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, "Invalid query")
    for params, exp_crashes in (({'op': 'OR', 'bucket': buckets[0].pk}, {crashes[0]}),
                                ({'op': 'OR', 'client__name': 'client #2'}, {crashes[1]}),
                                ({'op': 'OR', 'client__name__contains': '#2'}, {crashes[1]}),
                                ({'op': 'OR', 'client__name__contains': 'client'}, set(crashes)),
                                ({'op': 'OR', 'os__name': 'os #2'}, {crashes[1]}),
                                ({'op': 'NOT', 'os__name': 'os #2'}, {crashes[0]}),
                                ({'op': 'OR', 'product__name': 'product #2'}, {crashes[1]}),
                                ({'op': 'OR', 'platform__name': 'platform #2'}, {crashes[1]}),
                                ({'op': 'OR', 'testcase__quality': 3}, {crashes[1]}),
                                ({'op': 'OR', 'tool__name': 'tool #2'}, {crashes[1]}),
                                ({'op': 'OR', 'tool__name__contains': '#2'}, {crashes[1]})):
        LOG.debug('requesting with %r', params)
        LOG.debug('expecting: %r', exp_crashes)
        response = client.get(reverse("crashmanager:querycrashes"), {'query': json.dumps(params)})
        LOG.debug(response)
        assert response.status_code == requests.codes['ok']
        crashlist = response.context['crashlist']
        assert len(crashlist) == len(exp_crashes)  # num crashes
        assert set(crashlist) == exp_crashes  # expected crashes
        # pylint: disable=superfluous-parens
        assert_contains(response, ("Your search matched %d entries in database." % len(exp_crashes)))


def test_delete_testcase(cm):
    """Testcases should be delete when TestCase object is removed"""
    testcase = cm.create_testcase("test.txt", "hello world")
    test_file = testcase.test.name
    storage = testcase.test.storage
    assert storage.exists(test_file)
    testcase.delete()
    if storage.exists(test_file):
        storage.delete(test_file)
        raise AssertionError("file should have been deleted with TestCase: %r" % (test_file,))


def test_delete_testcase_crash(cm):
    """Testcases should be delete when CrashInfo object is removed"""
    testcase = cm.create_testcase("test.txt", "hello world")
    test_file = testcase.test.name
    storage = testcase.test.storage
    assert storage.exists(test_file)
    crash = cm.create_crash(testcase=testcase)
    crash.delete()
    if storage.exists(test_file):
        storage.delete(test_file)
        raise AssertionError("file should have been deleted with CrashInfo: %r" % (test_file,))
