'''
Tests for Crashes view.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import httplib
import logging

from django.core.urlresolvers import reverse
from django.core.files.base import ContentFile
from django.contrib.auth.models import User

from . import TestCase
from ..models import CrashEntry, Tool, Client, Platform, Product, OS, Bucket, TestCase as cmTestCase, User as cmUser


log = logging.getLogger("fm.crashmanager.tests.crashes")


class CrashesViewTests(TestCase):

    @staticmethod
    def create_crash(tool="testtool",
                     platform="testplatform",
                     product="testproduct",
                     os="testos",
                     testcase=None,
                     client="testclient",
                     bucket=None,
                     stdout="",
                     stderr="",
                     crashdata="",
                     metadata="",
                     env="",
                     args="",
                     crashAddress="",
                     crashAddressNumeric=None,
                     shortSignature="",
                     cachedCrashInfo="",
                     triagedOnce=False):
        # create tool
        tool, created = Tool.objects.get_or_create(name=tool)
        if created:
            log.debug("Created Tool pk=%d", tool.pk)
        # create platform
        platform, created = Platform.objects.get_or_create(name=platform)
        if created:
            log.debug("Created Platform pk=%d", platform.pk)
        # create product
        product, created = Product.objects.get_or_create(name=product)
        if created:
            log.debug("Created Product pk=%d", product.pk)
        # create os
        os, created = OS.objects.get_or_create(name=os)
        if created:
            log.debug("Created OS pk=%d", os.pk)
        # create client
        client, created = Client.objects.get_or_create(name=client)
        if created:
            log.debug("Created Client pk=%d", client.pk)
        result = CrashEntry.objects.create(tool=tool,
                                           platform=platform,
                                           product=product,
                                           os=os,
                                           testcase=testcase,
                                           client=client,
                                           bucket=bucket,
                                           rawStdout=stdout,
                                           rawStderr=stderr,
                                           rawCrashData=crashdata,
                                           metadata=metadata,
                                           env=env,
                                           args=args,
                                           crashAddress=crashAddress,
                                           crashAddressNumeric=crashAddressNumeric,
                                           shortSignature=shortSignature,
                                           cachedCrashInfo=cachedCrashInfo,
                                           triagedOnce=triagedOnce)
        log.debug("Created CrashEntry pk=%d", result.pk)
        return result

    @staticmethod
    def create_testcase(filename,
                        testdata="",
                        quality=0,
                        isBinary=False):
        result = cmTestCase(quality=quality, isBinary=isBinary, size=len(testdata))
        result.test.save(filename, ContentFile(testdata))
        result.save()
        return result

    @staticmethod
    def create_bucket(bug=None,
                      signature="",
                      shortDescription="",
                      frequent=False,
                      permanent=False):
        result = Bucket.objects.create(bug=bug,
                                       signature=signature,
                                       shortDescription=shortDescription,
                                       frequent=frequent,
                                       permanent=permanent)
        log.debug("Created Bucket pk=%d", result.pk)
        return result

    @staticmethod
    def create_toolfilter(tool):
        user = User.objects.get(username='test')
        cmuser, _ = cmUser.objects.get_or_create(user=user)
        cmuser.defaultToolsFilter.add(Tool.objects.get(name=tool))

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse('crashmanager:crashes')
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_no_crashes(self):
        """If no crashes in db, an appropriate message is shown."""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse('crashmanager:crashes'))
        self.assertEqual(response.status_code, httplib.OK)
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 0)  # 0 crashes
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertContains(response, "There are 0 unbucketed entries in the database.")

    def test_with_crash(self):
        """Insert one crash and check that it is shown ok."""
        self.client.login(username='test', password='test')
        crash = self.create_crash(shortSignature="crash #1")
        response = self.client.get(reverse('crashmanager:crashes'))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, "crash #1")
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 1)  # 1 crash
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertEqual(crashlist[0], crash)  # same crash we created
        self.assertContains(response, "There are 1 unbucketed entries in the database.")

    def test_with_crashes(self):
        """Insert two crashes and check that they are shown ok."""
        self.client.login(username='test', password='test')
        crash1 = self.create_crash(shortSignature="crash #1")
        crash2 = self.create_crash(shortSignature="crash #2")
        response = self.client.get(reverse('crashmanager:crashes'))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, "crash #1")
        self.assertContains(response, "crash #2")
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 2)  # 2 crashes
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertEqual(set(crashlist), {crash1, crash2})  # same crashes we created
        self.assertContains(response, "There are 2 unbucketed entries in the database.")

    def test_with_pagination(self):
        """Insert more than the page limit and check that they are paginated ok."""
        self.client.login(username='test', password='test')
        crashes = [self.create_crash(shortSignature="crash #1"),
                   self.create_crash(shortSignature="crash #2"),
                   self.create_crash(shortSignature="crash #3")]

        def check_page(page, exp_page, crash):
            response = self.client.get(reverse('crashmanager:crashes'), {'page': page, 'page_size': 1})
            self.assertEqual(response.status_code, httplib.OK)
            self.assertContains(response, crash.shortSignature)
            crashlist = response.context['crashlist']
            self.assertEqual(crashlist.number, exp_page)  # page num
            self.assertEqual(crashlist.paginator.num_pages, len(crashes))  # n pages total
            self.assertEqual(len(crashlist), 1)  # 1 crash/page
            self.assertEqual(crashlist[0], crash)  # same crash we created
            self.assertContains(response, "There are %d unbucketed entries in the database." % len(crashes))

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
        response = self.client.get(reverse('crashmanager:crashes'))
        self.assertEqual(response.status_code, httplib.OK)
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 0)  # 0 crashes
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertContains(response, "There are 0 unbucketed entries in the database.")

    def test_bucketed(self):
        """Insert two crashes and bucket one, see that unbucketed is shown."""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription="bucket #1")
        self.create_crash(shortSignature="crash #1", bucket=bucket)
        crash = self.create_crash(shortSignature="crash #2")
        response = self.client.get(reverse('crashmanager:crashes'))
        self.assertEqual(response.status_code, httplib.OK)
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 1)  # 1 crashes
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertEqual(crashlist[0], crash)  # same crash we created
        self.assertContains(response, "There are 1 unbucketed entries in the database.")

    def test_bucketed_all_param(self):
        """Check that all param shows bucketed crashes."""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription="bucket #1")
        crashes = [self.create_crash(shortSignature="crash #1", bucket=bucket),
                   self.create_crash(shortSignature="crash #2", bucket=bucket)]
        response = self.client.get(reverse('crashmanager:crashes'), {'all': 1})
        self.assertEqual(response.status_code, httplib.OK)
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 2)  # 2 crashes
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertEqual(set(crashlist), set(crashes))  # same crashes we created
        self.assertContains(response, "There are 2 unbucketed entries in the database.")  # XXX: this message is wrong

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
            response = self.client.get(reverse('crashmanager:crashes'), params)
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
        response = self.client.get(reverse('crashmanager:crashes'))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, "crash #1")
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 1)  # 1 crash
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertEqual(set(crashlist), {crashes[0]})  # same crashes we created
        self.assertContains(response, "There are 1 unbucketed entries in the database.")

    def test_all_view(self):
        """Check that crashes/all/ view disregards toolfilter."""
        self.client.login(username='test', password='test')
        crashes = (self.create_crash(shortSignature="crash #1", tool="tool #1"),
                   self.create_crash(shortSignature="crash #2", tool="tool #2"))
        self.create_toolfilter("tool #1")
        response = self.client.get(reverse('crashmanager:allcrashes'))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, "crash #1")
        self.assertContains(response, "crash #2")
        crashlist = response.context['crashlist']
        self.assertEqual(len(crashlist), 2)  # 2 crashes
        self.assertEqual(crashlist.number, 1)  # 1st page
        self.assertEqual(crashlist.paginator.num_pages, 1)  # 1 page total
        self.assertEqual(set(crashlist), set(crashes))  # same crashes we created
        self.assertContains(response, "Displaying all 2 entries in database.")
