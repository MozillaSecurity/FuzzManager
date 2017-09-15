'''
Tests for Crashes view.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import httplib
import json
import logging

from django.core.urlresolvers import reverse
import pytest

from . import TestCase
from ..models import CrashEntry


log = logging.getLogger("fm.crashmanager.tests.crashes")


class CrashesViewTests(TestCase):
    name = "crashmanager:crashes"
    entries_fmt = "There are %d unbucketed entries in the database."

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_no_crashes(self):
        """If no crashes in db, an appropriate message is shown."""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 0)  # 0 crashes
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertContains(response, self.entries_fmt % 0)

    def test_with_crash(self):
        """Insert one crash and check that it is shown ok."""
        self.client.login(username='test', password='test')
        crash = self.create_crash(shortSignature="crash #1")
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, "crash #1")
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 1)  # 1 crash
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertEqual(crashlist[0], crash)  # same crash we created
        self.assertContains(response, self.entries_fmt % 1)

    def test_with_crashes(self):
        """Insert two crashes and check that they are shown ok."""
        self.client.login(username='test', password='test')
        crash1 = self.create_crash(shortSignature="crash #1")
        crash2 = self.create_crash(shortSignature="crash #2")
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, "crash #1")
        self.assertContains(response, "crash #2")
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 2)  # 2 crashes
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertEqual(set(crashlist), {crash1, crash2})  # same crashes we created
        self.assertContains(response, self.entries_fmt % 2)

    def test_with_pagination(self):
        """Insert more than the page limit and check that they are paginated ok."""
        self.client.login(username='test', password='test')
        crashes = [self.create_crash(shortSignature="crash #1"),
                   self.create_crash(shortSignature="crash #2"),
                   self.create_crash(shortSignature="crash #3")]

        def check_page(page, exp_page, crash):
            response = self.client.get(reverse(self.name), {'page': page, 'page_size': 1})
            self.assertEqual(response.status_code, httplib.OK)
            self.assertContains(response, crash.shortSignature)
            crashlist = response.context['crashlist']
            self.assertEqual(crashlist.number, exp_page)  # page num
            self.assertEqual(crashlist.paginator.num_pages, len(crashes))  # n pages total
            self.assertEqual(len(crashlist), 1)  # 1 crash/page
            self.assertEqual(crashlist[0], crash)  # same crash we created
            self.assertContains(response, self.entries_fmt % len(crashes))

        for page, crash in enumerate(reversed(crashes)):
            check_page(page + 1, page + 1, crash)
        # check invalid page params
        check_page(len(crashes) + 1, len(crashes), crashes[0])  # out of range will return last page
        check_page(-1, len(crashes), crashes[0])  # out of range will return last page
        check_page("blah", 1, crashes[-1])  # non-integer will return first page

    def test_no_unbucketed(self):
        """Insert one crash and bucket it, and see that no entries are shown."""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription="bucket #1")
        self.create_crash(shortSignature="crash #1", bucket=bucket)
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 0)  # 0 crashes
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertContains(response, self.entries_fmt % 0)

    def test_bucketed(self):
        """Insert two crashes and bucket one, see that unbucketed is shown."""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription="bucket #1")
        self.create_crash(shortSignature="crash #1", bucket=bucket)
        crash = self.create_crash(shortSignature="crash #2")
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 1)  # 1 crashes
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertEqual(crashlist[0], crash)  # same crash we created
        self.assertContains(response, self.entries_fmt % 1)

    def test_bucketed_all_param(self):
        """Check that all param shows bucketed crashes."""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription="bucket #1")
        crashes = [self.create_crash(shortSignature="crash #1", bucket=bucket),
                   self.create_crash(shortSignature="crash #2", bucket=bucket)]
        response = self.client.get(reverse(self.name), {'all': 1})
        self.assertEqual(response.status_code, httplib.OK)
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 2)  # 2 crashes
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertEqual(set(crashlist), set(crashes))  # same crashes we created
        self.assertContains(response, self.entries_fmt % 2)  # XXX: this message is wrong

    def test_filters(self):
        """Check that filter params are respected."""
        self.client.login(username='test', password='test')
        buckets = [self.create_bucket(shortDescription="bucket #1"),
                   None]
        testcases = [None,
                     self.create_testcase("test.txt", quality=3)]
        crashes = [self.create_crash(shortSignature="crash #%d" % (i + 1),
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
            log.debug('requesting with %r', params)
            log.debug('expecting: %r', exp_crashes)
            response = self.client.get(reverse(self.name), params)
            self.assertEqual(response.status_code, httplib.OK)
            crashlist = response.context['crashlist']
            self.assertEqual(len(crashlist), len(exp_crashes))  # num crashes
            self.assertEqual(crashlist.number, 1)  # 1st page
            self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
            self.assertEqual(set(crashlist), exp_crashes)  # expected crashes
            self.assertContains(response, "Your search matched %d entries in database." % len(exp_crashes))

    def test_toolfilter(self):
        """Create a toolfilter and see that it is respected."""
        self.client.login(username='test', password='test')
        crashes = (self.create_crash(shortSignature="crash #1", tool="tool #1"),
                   self.create_crash(shortSignature="crash #2", tool="tool #2"))
        self.create_toolfilter("tool #1")
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, "crash #1")
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 1)  # 1 crash
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertEqual(set(crashlist), {crashes[0]})  # same crashes we created
        self.assertContains(response, self.entries_fmt % 1)


class AllCrashesViewTests(CrashesViewTests):
    name = "crashmanager:allcrashes"
    entries_fmt = "Displaying all %d entries in database."

    @pytest.mark.xfail
    def test_filters(self):
        super(AllCrashesViewTests, self).test_filters()

    @pytest.mark.xfail
    def test_bucketed(self):
        super(AllCrashesViewTests, self).test_bucketed()

    @pytest.mark.xfail
    def test_no_unbucketed(self):
        super(AllCrashesViewTests, self).test_no_unbucketed()

    def test_toolfilter(self):
        """Check that crashes/all/ view disregards toolfilter."""
        self.client.login(username='test', password='test')
        crashes = (self.create_crash(shortSignature="crash #1", tool="tool #1"),
                   self.create_crash(shortSignature="crash #2", tool="tool #2"))
        self.create_toolfilter("tool #1")
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, "crash #1")
        self.assertContains(response, "crash #2")
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 2)  # 2 crashes
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertEqual(set(crashlist), set(crashes))  # same crashes we created
        self.assertContains(response, self.entries_fmt % 2)


class AutoAssignCrashesTests(TestCase):
    name = "crashmanager:autoassign"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_autoassign(self):
        """Create crashes and a signature that would match it and see that autoassign buckets it"""
        self.client.login(username='test', password='test')
        crash = self.create_crash(shortSignature='crash #1', stderr="blah")
        sig = json.dumps({
            'symptoms': [
                {"src": "stderr",
                 "type": "output",
                 "value": "/^blah/"}
            ]
        })
        bucket = self.create_bucket(shortDescription='bucket #1', signature=sig)
        crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
        self.assertIsNone(crash.bucket)
        self.assertRedirects(self.client.get(reverse(self.name)), reverse('crashmanager:crashes'))
        crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
        self.assertEqual(crash.bucket, bucket)


class QueryCrashesTests(TestCase):
    name = "crashmanager:querycrashes"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_query(self):
        """Crash list queries"""
        self.client.login(username='test', password='test')
        buckets = [self.create_bucket(shortDescription="bucket #1"),
                   None]
        testcases = [None,
                     self.create_testcase("test.txt", quality=3)]
        crashes = [self.create_crash(shortSignature="crash #%d" % (i + 1),
                                     client="client #%d" % (i + 1),
                                     os="os #%d" % (i + 1),
                                     product="product #%d" % (i + 1),
                                     platform="platform #%d" % (i + 1),
                                     tool="tool #%d" % (i + 1),
                                     bucket=buckets[i],
                                     testcase=testcases[i])
                   for i in range(2)]
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, "Search Query")
        self.assertNotContains(response, "Invalid query")
        response = self.client.get(reverse(self.name), {"query": "badjson"})
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, "Invalid query")
        response = self.client.post(reverse(self.name), {"query": "badjson"})
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, "Invalid query")
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
            log.debug('requesting with %r', params)
            log.debug('expecting: %r', exp_crashes)
            response = self.client.get(reverse(self.name), {'query': json.dumps(params)})
            self.assertEqual(response.status_code, httplib.OK)
            crashlist = response.context['crashlist']
            self.assertEqual(len(crashlist), len(exp_crashes))  # num crashes
            self.assertEqual(set(crashlist), exp_crashes)  # expected crashes
            self.assertContains(response, "Your search matched %d entries in database." % len(exp_crashes))
