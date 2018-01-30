'''
Tests for signatures view.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import json
import logging

import requests
from django.core.urlresolvers import reverse

from . import TestCase
from ..models import Bucket, BucketWatch, CrashEntry


log = logging.getLogger("fm.crashmanager.tests.signatures")  # pylint: disable=invalid-name


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
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        siglist = response.context['siglist']
        self.assertEqual(len(siglist), 0)  # 0 buckets
        self.assertContains(response, self.entries_fmt % 0)

    def test_with_sig(self):
        """Create one bucket and check that it is shown ok."""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription="bucket #1")
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
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
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
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
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        siglist = response.context['siglist']
        self.assertEqual(len(siglist), 0)  # 0 buckets
        self.assertContains(response, self.entries_fmt % 0)

    def test_logged_unlogged(self):
        """Create two buckets and mark one logged, see that only unlogged entry is shown."""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription="bucket #1")
        self.create_bucket(shortDescription="bucket #2", bug=self.create_bug('123'))
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
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
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
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
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
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
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
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
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
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


class FindSignatureTests(TestCase):
    name = "crashmanager:findsigs"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'crashid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        crash = self.create_crash()
        self.create_bucket(signature=json.dumps({"symptoms": [
            {'src': 'stderr',
             'type': 'output',
             'value': '//'}]}))

        response = self.client.get(reverse(self.name, kwargs={"crashid": crash.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class LinkSignatureTests(TestCase):
    name = "crashmanager:siglink"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'sigid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket()
        response = self.client.get(reverse(self.name, kwargs={"sigid": bucket.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class UnlinkSignatureTests(TestCase):
    name = "crashmanager:sigunlink"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'sigid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket()
        response = self.client.get(reverse(self.name, kwargs={"sigid": bucket.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class OptSignatureTests(TestCase):
    name = "crashmanager:sigopt"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'sigid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(signature=json.dumps({"symptoms": [
            {'src': 'stderr',
             'type': 'output',
             'value': '//'}]}))
        response = self.client.get(reverse(self.name, kwargs={"sigid": bucket.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class TrySignatureTests(TestCase):
    name = "crashmanager:sigtry"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'sigid': 0, 'crashid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(signature=json.dumps({"symptoms": [
            {'src': 'stderr',
             'type': 'output',
             'value': '//'}]}))
        crash = self.create_crash()
        response = self.client.get(reverse(self.name, kwargs={"sigid": bucket.pk, "crashid": crash.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class NewSignatureTests(TestCase):
    name = "crashmanager:signew"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_new(self):
        """Check that the form looks ok"""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertContains(response, 'name="shortDescription"')
        self.assertContains(response, 'name="signature"')
        self.assertContains(response, 'name="frequent"')
        self.assertContains(response, 'name="reassign"')

    def test_create(self):
        """Create signature from scratch, not reassigning crashes"""
        self.client.login(username='test', password='test')
        sig = json.dumps({
            'symptoms': [
                {"src": "stderr",
                 "type": "output",
                 "value": "/^blah/"}
            ]
        })
        crash = self.create_crash(shortSignature='crash #1', stderr="blah")
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

    def test_create_w_reassign(self):
        """Create signature from scratch and reassign a crash"""
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

    def test_create_w_reassign_many(self):
        """Create signature from scratch and reassign many crashes"""
        self.client.login(username='test', password='test')
        crashes = [self.create_crash(shortSignature='crash #1', stderr="blah") for _ in range(201)]
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
        crashes = [CrashEntry.objects.get(pk=crash.pk) for crash in crashes]  # re-read
        for crash in crashes:
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
        self.assertContains(response, ('New issues that will be assigned to this bucket '
                                       '(<a href="#crashes_in">list</a>): <span class="badge">1</span>'))
        self.assertContains(response, 'New issues that will be assigned to this bucket:')

    def test_preview_many(self):
        """Preview signature with crash matching"""
        self.client.login(username='test', password='test')
        crashes = [self.create_crash(shortSignature='crash #1', stderr="blah") for _ in range(201)]
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
        self.assertEqual(len(in_list), 100)
        self.assertEqual(len(out_list), 0)
        self.assertEqual(response.context['inListCount'], 201)
        for crash in crashes:
            crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
            self.assertIsNone(crash.bucket)
        for shown, crash in zip(reversed(in_list), crashes[-100:]):
            self.assertEqual(shown, crash)
        self.assertContains(response, ('New issues that will be assigned to this bucket '
                                       '(<a href="#crashes_in">list</a>): <span class="badge">201</span>'))
        self.assertContains(response, 'New issues that will be assigned to this bucket (truncated):')

    def test_new_from_crash(self):
        """Check that the form includes crash info when creating from crash"""
        self.client.login(username='test', password='test')
        stderr = "Program received signal SIGSEGV, Segmentation fault.\n#0  sym_a ()\n#1  sym_b ()"
        crash = self.create_crash(shortSignature='crash #1', stderr=stderr)
        response = self.client.get(reverse(self.name) + '?crashid=%d' % crash.pk)
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertContains(response, 'name="shortDescription"')
        self.assertContains(response, 'name="signature"')
        self.assertContains(response, 'name="frequent"')
        self.assertContains(response, 'name="reassign"')

        # check that it looks like a signature was created from our crash
        self.assertContains(response, 'symptoms')
        self.assertContains(response, 'stackFrames')
        self.assertContains(response, 'sym_a')
        self.assertContains(response, 'sym_b')

        # create a bucket from the proposed signature and see that it matches the crash
        sig = response.context['bucket']['signature']
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


class EditSignatureTests(TestCase):
    name = "crashmanager:sigedit"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'sigid': 1})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_edit(self):
        """Check that the form looks ok"""
        self.client.login(username='test', password='test')
        sig = json.dumps({
            'symptoms': [
                {"src": "stderr",
                 "type": "output",
                 "value": "/^blah/"}
            ]
        })
        bucket = self.create_bucket(shortDescription="bucket #1", signature=sig)
        response = self.client.get(reverse(self.name, kwargs={'sigid': bucket.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertContains(response, 'name="shortDescription"')
        self.assertContains(response, 'name="signature"')
        self.assertContains(response, 'name="frequent"')
        self.assertContains(response, 'name="reassign"')
        self.assertContains(response, 'symptoms')
        self.assertContains(response, 'stderr')
        self.assertContains(response, 'blah')
        self.assertContains(response, 'bucket #1')

    def test_edit_w_reassign(self):
        """Edit signature and reassign a crash"""
        self.client.login(username='test', password='test')
        crash = self.create_crash(shortSignature='crash #1', stderr="blah")
        bucket = self.create_bucket()
        sig = json.dumps({
            'symptoms': [
                {"src": "stderr",
                 "type": "output",
                 "value": "/^blah/"}
            ]
        })
        path = reverse(self.name, kwargs={'sigid': bucket.pk})
        response = self.client.post(path, {'shortDescription': 'bucket #1',
                                           'signature': sig,
                                           'reassign': '1',
                                           'submit_save': '1'})
        log.debug(response)
        bucket = Bucket.objects.get(pk=bucket.pk)  # re-read
        self.assertEqual(json.loads(bucket.signature), json.loads(sig))
        self.assertEqual(bucket.shortDescription, "bucket #1")
        crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
        self.assertEqual(crash.bucket, bucket)
        self.assertFalse(bucket.frequent)
        self.assertFalse(bucket.permanent)
        self.assertRedirects(response, reverse('crashmanager:sigview', kwargs={'sigid': bucket.pk}))

    def test_edit_w_reassign_many(self):
        """Edit signature and reassign many crashes"""
        self.client.login(username='test', password='test')
        crashes = [self.create_crash(shortSignature='crash #1', stderr="blah") for _ in range(201)]
        bucket = self.create_bucket()
        sig = json.dumps({
            'symptoms': [
                {"src": "stderr",
                 "type": "output",
                 "value": "/^blah/"}
            ]
        })
        path = reverse(self.name, kwargs={'sigid': bucket.pk})
        response = self.client.post(path, {'shortDescription': 'bucket #1',
                                           'signature': sig,
                                           'reassign': '1',
                                           'submit_save': '1'})
        log.debug(response)
        bucket = Bucket.objects.get(pk=bucket.pk)  # re-read
        self.assertEqual(json.loads(bucket.signature), json.loads(sig))
        self.assertEqual(bucket.shortDescription, "bucket #1")
        for crash in crashes:
            crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
            self.assertEqual(crash.bucket, bucket)
        self.assertFalse(bucket.frequent)
        self.assertFalse(bucket.permanent)
        self.assertRedirects(response, reverse('crashmanager:sigview', kwargs={'sigid': bucket.pk}))

    def test_preview(self):
        """Preview signature edit with crash matching"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket()
        crash1 = self.create_crash(shortSignature='crash #1', stderr="foo", bucket=bucket)
        crash2 = self.create_crash(shortSignature='crash #2', stderr="blah")
        sig = json.dumps({
            'symptoms': [
                {"src": "stderr",
                 "type": "output",
                 "value": "/^blah/"}
            ]
        })
        path = reverse(self.name, kwargs={'sigid': bucket.pk})
        response = self.client.post(path, {'shortDescription': 'bucket #1',
                                           'signature': sig,
                                           'reassign': '1'})
        log.debug(response)
        bucket = Bucket.objects.get(pk=bucket.pk)  # re-read
        in_list = response.context['inList']
        out_list = response.context['outList']
        self.assertEqual(len(in_list), 1)
        self.assertEqual(len(out_list), 1)
        crash1 = CrashEntry.objects.get(pk=crash1.pk)  # re-read
        crash2 = CrashEntry.objects.get(pk=crash2.pk)  # re-read
        self.assertEqual(crash1.bucket, bucket)
        self.assertIsNone(crash2.bucket)
        self.assertEqual(out_list[0], crash1)
        self.assertEqual(in_list[0], crash2)
        self.assertContains(response, ('New issues that will be assigned to this bucket '
                                       '(<a href="#crashes_in">list</a>): <span class="badge">1</span>'))
        self.assertContains(response, ('Issues that will be removed from this bucket '
                                       '(<a href="#crashes_out">list</a>): <span class="badge">1</span>'))
        self.assertContains(response, 'New issues that will be assigned to this bucket:')
        self.assertContains(response, 'Issues that will be removed from this bucket:')

    def test_preview_many(self):
        """Preview signature edit with crash matching"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket()
        crashes1 = [self.create_crash(shortSignature='crash #1', stderr="foo", bucket=bucket) for _ in range(201)]
        crashes2 = [self.create_crash(shortSignature='crash #2', stderr="blah") for _ in range(201)]
        sig = json.dumps({
            'symptoms': [
                {"src": "stderr",
                 "type": "output",
                 "value": "/^blah/"}
            ]
        })
        path = reverse(self.name, kwargs={'sigid': bucket.pk})
        response = self.client.post(path, {'shortDescription': 'bucket #1',
                                           'signature': sig,
                                           'reassign': '1'})
        log.debug(response)
        bucket = Bucket.objects.get(pk=bucket.pk)  # re-read
        in_list = response.context['inList']
        out_list = response.context['outList']
        self.assertEqual(len(in_list), 100)
        self.assertEqual(len(out_list), 100)
        self.assertEqual(response.context['inListCount'], 201)
        self.assertEqual(response.context['outListCount'], 201)
        for crash in crashes1:
            crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
            self.assertEqual(crash.bucket, bucket)
        for crash in crashes2:
            crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
            self.assertIsNone(crash.bucket)
        for shown, crash in zip(reversed(in_list), crashes2[-100:]):
            self.assertEqual(shown, crash)
        for shown, crash in zip(reversed(out_list), crashes1[-100:]):
            self.assertEqual(shown, crash)
        self.assertContains(response, ('New issues that will be assigned to this bucket '
                                       '(<a href="#crashes_in">list</a>): <span class="badge">201</span>'))
        self.assertContains(response, ('Issues that will be removed from this bucket '
                                       '(<a href="#crashes_out">list</a>): <span class="badge">201</span>'))
        self.assertContains(response, 'New issues that will be assigned to this bucket (truncated):')
        self.assertContains(response, 'Issues that will be removed from this bucket (truncated):')


class DelSignatureTests(TestCase):
    name = 'crashmanager:sigdel'
    entries_fmt = "Also delete all %d entries with this bucket"

    def test_template(self):
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription='bucket #1')
        response = self.client.get(reverse(self.name, kwargs={"sigid": bucket.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertContains(response, "Are you sure that you want to delete this signature?")
        self.assertContains(response, self.entries_fmt % 0)
        self.create_crash(shortSignature='crash #1', bucket=bucket)
        response = self.client.get(reverse(self.name, kwargs={"sigid": bucket.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertContains(response, "Are you sure that you want to delete this signature?")
        self.assertContains(response, self.entries_fmt % 1)

    def test_empty(self):
        """Test deleting a signature with no crashes"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription='bucket #1')
        response = self.client.post(reverse(self.name, kwargs={"sigid": bucket.pk}))
        log.debug(response)
        self.assertRedirects(response, reverse('crashmanager:signatures'))
        self.assertEqual(Bucket.objects.count(), 0)

    def test_leave_entries(self):
        """Test deleting a signature with crashes and leave entries"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription='bucket #1')
        crash = self.create_crash(shortSignature='crash #1', bucket=bucket)
        response = self.client.post(reverse(self.name, kwargs={"sigid": bucket.pk}))
        log.debug(response)
        self.assertRedirects(response, reverse('crashmanager:signatures'))
        self.assertEqual(Bucket.objects.count(), 0)
        crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
        self.assertIsNone(crash.bucket)

    def test_del_entries(self):
        """Test deleting a signature with crashes and removing entries"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription='bucket #1')
        self.create_crash(shortSignature='crash #1', bucket=bucket)
        response = self.client.post(reverse(self.name, kwargs={"sigid": bucket.pk}), {'delentries': '1'})
        log.debug(response)
        self.assertRedirects(response, reverse('crashmanager:signatures'))
        self.assertEqual(Bucket.objects.count(), 0)
        self.assertEqual(CrashEntry.objects.count(), 0)


class WatchSignatureTests(TestCase):

    def test_empty(self):
        """If no watched signatures, that should be shown"""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse('crashmanager:sigwatch'))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertContains(response, "Displaying 0 watched signature entries from the database.")

    def test_buckets(self):
        """Watched signatures should be listed"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription='bucket #1')
        self.create_bucketwatch(bucket=bucket)
        response = self.client.get(reverse('crashmanager:sigwatch'))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertContains(response, "Displaying 1 watched signature entries from the database.")
        siglist = response.context['siglist']
        self.assertEqual(len(siglist), 1)
        self.assertEqual(siglist[0], bucket)

    def test_buckets_new_crashes(self):
        """Watched signatures should show new crashes"""
        self.client.login(username='test', password='test')
        buckets = (self.create_bucket(shortDescription='bucket #1'),
                   self.create_bucket(shortDescription='bucket #2'))
        crash1 = self.create_crash(shortSignature='crash #1', bucket=buckets[1], tool='tool #1')
        self.create_toolfilter('tool #1')
        self.create_bucketwatch(bucket=buckets[0])
        self.create_bucketwatch(bucket=buckets[1], crash=crash1)
        self.create_crash(shortSignature='crash #2', bucket=buckets[1], tool='tool #1')
        response = self.client.get(reverse('crashmanager:sigwatch'))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertContains(response, "Displaying 2 watched signature entries from the database.")
        siglist = response.context['siglist']
        self.assertEqual(len(siglist), 2)
        self.assertEqual(siglist[0], buckets[1])
        self.assertEqual(siglist[0].newCrashes, 1)
        self.assertEqual(siglist[1], buckets[0])
        self.assertEqual(siglist[1].newCrashes, 0)

    def test_del(self):
        """Deleting a signature watch"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription='bucket #1')
        self.create_bucketwatch(bucket=bucket)
        response = self.client.get(reverse('crashmanager:sigwatchdel', kwargs={"sigid": bucket.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertContains(response,
                            "Are you sure that you want to stop watching this signature for new crash entries?")
        self.assertContains(response, bucket.shortDescription)
        response = self.client.post(reverse('crashmanager:sigwatchdel', kwargs={"sigid": bucket.pk}))
        log.debug(response)
        self.assertEqual(BucketWatch.objects.count(), 0)
        self.assertEqual(Bucket.objects.get(), bucket)
        self.assertRedirects(response, reverse('crashmanager:sigwatch'))

    def test_delsig(self):
        """Deleting a watched signature"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription='bucket #1')
        self.create_bucketwatch(bucket=bucket)
        bucket.delete()
        self.assertEqual(BucketWatch.objects.count(), 0)

    def test_update(self):
        """Updating a signature watch"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription="bucket #1")
        crash1 = self.create_crash(shortSignature='crash #1', bucket=bucket)
        watch = self.create_bucketwatch(bucket=bucket, crash=crash1)
        crash2 = self.create_crash(shortSignature='crash #2', bucket=bucket)
        response = self.client.post(reverse('crashmanager:sigwatchnew'), {"bucket": "%d" % bucket.pk,
                                                                          "crash": "%d" % crash2.pk})
        log.debug(response)
        self.assertRedirects(response, reverse('crashmanager:sigwatch'))
        watch = BucketWatch.objects.get(pk=watch.pk)
        self.assertEqual(watch.bucket, bucket)
        self.assertEqual(watch.lastCrash, crash2.pk)

    def test_new(self):
        """Creating a signature watch"""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription="bucket #1")
        crash = self.create_crash(shortSignature='crash #1', bucket=bucket)
        response = self.client.post(reverse('crashmanager:sigwatchnew'), {"bucket": "%d" % bucket.pk,
                                                                          "crash": "%d" % crash.pk})
        log.debug(response)
        self.assertRedirects(response, reverse('crashmanager:sigwatch'))
        watch = BucketWatch.objects.get()
        self.assertEqual(watch.bucket, bucket)
        self.assertEqual(watch.lastCrash, crash.pk)

    def test_crashes(self):
        """Crashes in a signature watch should be shown correctly."""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription='bucket #1')
        crash1 = self.create_crash(shortSignature='crash #1', bucket=bucket)
        url = reverse("crashmanager:sigwatchcrashes", kwargs={"sigid": bucket.pk})
        watch = self.create_bucketwatch(bucket=bucket)
        # check that crash1 is shown
        response = self.client.get(url)
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        crashes = response.context['crashlist']
        self.assertEqual(len(crashes), 1)
        self.assertEqual(crashes[0], crash1)
        watch.lastCrash = crash1.pk
        watch.save()
        # check that no crashes are shown
        response = self.client.get(url)
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        crashes = response.context['crashlist']
        self.assertEqual(len(crashes), 0)
        crash2 = self.create_crash(shortSignature='crash #2', bucket=bucket)
        # check that crash2 is shown
        response = self.client.get(url)
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        crashes = response.context['crashlist']
        self.assertEqual(len(crashes), 1)
        self.assertEqual(crashes[0], crash2)
