'''
Tests for signatures view.

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
from django.core.files.base import ContentFile
from django.contrib.auth.models import User

from . import TestCase
from ..models import Bucket, CrashEntry


log = logging.getLogger("fm.crashmanager.tests.signatures")


class SignaturesViewTests(TestCase):
    name = "crashmanager:signatures"
    entries_fmt = "Displaying %d unreported signature entries from the database."

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_no_sigs(self):
        """If no sigs in db, an appropriate message is shown."""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        siglist = response.context['siglist']
        self.assertEqual(len(siglist), 0)  # 0 buckets
        self.assertContains(response, self.entries_fmt % 0)

    def test_with_sig(self):
        """Create one bucket and check that it is shown ok."""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription="bucket #1")
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        siglist = response.context['siglist']
        self.assertEqual(len(siglist), 1)  # 1 bucket
        self.assertEqual(siglist[0], bucket)  # same bucket we created
        self.assertContains(response, "bucket #1")
        self.assertContains(response, self.entries_fmt % 1)

    def test_with_sigs(self):
        """Create two buckets and check that they are shown ok."""
        self.client.login(username='test', password='test')
        buckets = (self.create_bucket(shortDescription="bucket #1"),
                   self.create_bucket(shortDescription="bucket #2"))
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        siglist = response.context['siglist']
        self.assertEqual(len(siglist), 2)  # 2 buckets
        self.assertEqual(set(siglist), set(buckets))  # same buckets we created
        self.assertContains(response, "bucket #1")
        self.assertContains(response, "bucket #2")
        self.assertContains(response, self.entries_fmt % 2)

    def test_logged(self):
        """Create a bucket and mark it logged, see that no entries are shown."""
        self.client.login(username='test', password='test')
        self.create_bucket(shortDescription="bucket #1", bug=self.create_bug('123'))
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        siglist = response.context['siglist']
        self.assertEqual(len(siglist), 0)  # 0 buckets
        self.assertContains(response, self.entries_fmt % 0)

    def test_logged_unlogged(self):
        """Create two buckets and mark one logged, see that only unlogged entry is shown."""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription="bucket #1")
        self.create_bucket(shortDescription="bucket #2", bug=self.create_bug('123'))
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        siglist = response.context['siglist']
        self.assertEqual(len(siglist), 1)  # 1 bucket
        self.assertEqual(siglist[0], bucket)  # same bucket we created
        self.assertContains(response, "bucket #1")
        self.assertContains(response, self.entries_fmt % 1)

    def test_toolfilter(self):
        """Check that toolfilter affects bucket size."""
        self.client.login(username='test', password='test')
        bucket1 = self.create_bucket(shortDescription="bucket #1")
        bucket2 = self.create_bucket(shortDescription="bucket #2")
        self.create_crash(shortSignature="crash #1", tool="tool #1", bucket=bucket1)
        self.create_crash(shortSignature="crash #2", tool="tool #2", bucket=bucket1)
        self.create_crash(shortSignature="crash #3", tool="tool #1", bucket=bucket1)
        self.create_crash(shortSignature="crash #4", tool="tool #1", bucket=bucket2)
        self.create_toolfilter("tool #1")
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        siglist = response.context['siglist']
        log.debug(siglist)
        self.assertEqual(len(siglist), 2)  # 2 buckets
        self.assertEqual(siglist[0], bucket2)
        self.assertEqual(siglist[0].size, 1)
        self.assertEqual(siglist[1], bucket1)
        self.assertEqual(siglist[1].size, 2)
        self.assertContains(response, "bucket #1")
        self.assertContains(response, "bucket #2")
        self.assertContains(response, self.entries_fmt % 2)


class AllSignaturesViewTests(SignaturesViewTests):
    name = "crashmanager:allsignatures"
    entries_fmt = "Displaying all %d signature entries in the database."

    def test_logged(self):
        """Create a bucket, mark logged, and see that /all/ still shows the entry."""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription="bucket #1", bug=self.create_bug('123'))
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, "bucket #1")
        siglist = response.context['siglist']
        self.assertEqual(len(siglist), 1)  # 1 bucket
        self.assertEqual(siglist[0], bucket)  # same bucket we created
        self.assertContains(response, self.entries_fmt % 1)

    def test_logged_unlogged(self):
        """Create a bucket, mark logged, and see that /all/ shows both entries."""
        self.client.login(username='test', password='test')
        buckets = (self.create_bucket(shortDescription="bucket #1"),
                   self.create_bucket(shortDescription="bucket #2", bug=self.create_bug('123')))
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        siglist = response.context['siglist']
        self.assertEqual(len(siglist), 2)  # 2 buckets
        self.assertEqual(set(siglist), set(buckets))  # same buckets we created
        self.assertContains(response, "bucket #1")
        self.assertContains(response, "bucket #2")
        self.assertContains(response, self.entries_fmt % 2)

    def test_toolfilter(self):
        """Check that toolfilter is ignored in /all/."""
        self.client.login(username='test', password='test')
        bucket1 = self.create_bucket(shortDescription="bucket #1")
        bucket2 = self.create_bucket(shortDescription="bucket #2")
        self.create_crash(shortSignature="crash #1", tool="tool #1", bucket=bucket1)
        self.create_crash(shortSignature="crash #2", tool="tool #2", bucket=bucket1)
        self.create_crash(shortSignature="crash #3", tool="tool #1", bucket=bucket1)
        self.create_crash(shortSignature="crash #4", tool="tool #1", bucket=bucket2)
        self.create_toolfilter("tool #1")
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        siglist = response.context['siglist']
        log.debug(siglist)
        self.assertEqual(len(siglist), 2)  # 2 buckets
        self.assertEqual(siglist[0], bucket2)
        self.assertEqual(siglist[0].size, 1)
        self.assertEqual(siglist[1], bucket1)
        self.assertEqual(siglist[1].size, 3)
        self.assertContains(response, "bucket #1")
        self.assertContains(response, "bucket #2")
        self.assertContains(response, self.entries_fmt % 2)


class NewSignatureTests(TestCase):
    name = "crashmanager:signew"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_new(self):
        """Create signature from scratch, not reassigning crashes"""
        self.client.login(username='test', password='test')
        crash = self.create_crash(shortSignature='crash #1', stderr="blah")
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, 'name="shortDescription"')
        self.assertContains(response, 'name="signature"')
        self.assertContains(response, 'name="frequent"')
        self.assertContains(response, 'name="reassign"')
        sig = json.dumps({
            'symptoms': [
                {"src": "stderr",
                 "type": "output",
                 "value": "/^blah/"}
            ]
        })
        response = self.client.post(reverse(self.name), {'shortDescription': 'bucket #1',
                                                         'signature': sig,
                                                         'submit_save': '1'})
        log.debug(response)
        bucket = Bucket.objects.get(shortDescription='bucket #1')
        crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
        self.assertIsNone(crash.bucket)
        self.assertFalse(bucket.frequent)
        self.assertFalse(bucket.permanent)
        self.assertRedirects(response, reverse('crashmanager:sigview', kwargs={'sigid': bucket.pk}))

    def test_new_w_crashes(self):
        """Create signature from scratch and reassign crashes"""
        self.client.login(username='test', password='test')
        crash = self.create_crash(shortSignature='crash #1', stderr="blah")
        sig = json.dumps({
            'symptoms': [
                {"src": "stderr",
                 "type": "output",
                 "value": "/^blah/"}
            ]
        })
        response = self.client.post(reverse(self.name), {'shortDescription': 'bucket #1',
                                                         'signature': sig,
                                                         'reassign': '1',
                                                         'submit_save': '1'})
        log.debug(response)
        bucket = Bucket.objects.get(shortDescription='bucket #1')
        crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
        self.assertEqual(crash.bucket, bucket)
        self.assertFalse(bucket.frequent)
        self.assertFalse(bucket.permanent)
        self.assertRedirects(response, reverse('crashmanager:sigview', kwargs={'sigid': bucket.pk}))

    def test_preview(self):
        """Preview signature with crash matching"""
        self.client.login(username='test', password='test')
        crash = self.create_crash(shortSignature='crash #1', stderr="blah")
        sig = json.dumps({
            'symptoms': [
                {"src": "stderr",
                 "type": "output",
                 "value": "/^blah/"}
            ]
        })
        response = self.client.post(reverse(self.name), {'shortDescription': 'bucket #1',
                                                         'signature': sig,
                                                         'reassign': '1'})
        log.debug(response)
        self.assertFalse(Bucket.objects.filter(shortDescription='bucket #1').exists())
        in_list = response.context['inList']
        out_list = response.context['outList']
        self.assertEqual(len(in_list), 1)
        self.assertEqual(len(out_list), 0)
        crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
        self.assertIsNone(crash.bucket)
        self.assertEqual(in_list[0], crash)

    def test_new_from_crash(self):
        """Create signature from crash"""
        self.client.login(username='test', password='test')
        stderr = "Program received signal SIGSEGV, Segmentation fault.\n#0  sym_a ()\n#1  sym_b ()"
        crash = self.create_crash(shortSignature='crash #1', stderr=stderr)
        response = self.client.get(reverse(self.name) + '?crashid=%d' % crash.pk)
        self.assertEqual(response.status_code, httplib.OK)
        self.assertContains(response, 'name="shortDescription"')
        self.assertContains(response, 'name="signature"')
        self.assertContains(response, 'name="frequent"')
        self.assertContains(response, 'name="reassign"')
        # check that it looks like a signature was created from our crash
        self.assertContains(response, 'symptoms')
        self.assertContains(response, 'stackFrames')
        self.assertContains(response, 'sym_a')
        self.assertContains(response, 'sym_b')
