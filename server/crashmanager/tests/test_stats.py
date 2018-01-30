'''
Tests for stats view.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import datetime
import logging

import requests
from django.core.urlresolvers import reverse

from . import TestCase


log = logging.getLogger("fm.crashmanager.tests.stats")  # pylint: disable=invalid-name


class StatsViewTests(TestCase):
    name = "crashmanager:stats"
    entries_fmt = "Total reports in the last hour: %d"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_no_crashes(self):
        """If no crashes in db, an appropriate message is shown."""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertEqual(response.context['total_reports_per_hour'], 0)
        self.assertContains(response, self.entries_fmt % 0)
        self.assertEqual(len(response.context['frequentBuckets']), 0)

    def test_with_crash(self):
        """Insert one crash and check that it is shown ok."""
        self.client.login(username='test', password='test')
        self.create_crash(shortSignature="crash #1")
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertEqual(response.context['total_reports_per_hour'], 1)
        self.assertContains(response, self.entries_fmt % 1)
        self.assertEqual(len(response.context['frequentBuckets']), 0)

    def test_with_crashes(self):
        """Insert crashes and check that they are shown ok."""
        self.client.login(username='test', password='test')
        bucket = self.create_bucket(shortDescription="bucket #1")
        self.create_crash(shortSignature="crash #1", tool="tool #1")
        self.create_crash(shortSignature="crash #2", tool="tool #1", bucket=bucket)
        self.create_crash(shortSignature="crash #3", tool="tool #1", bucket=bucket)
        self.create_crash(shortSignature="crash #4", tool="tool #2")
        self.create_toolfilter("tool #1")
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertEqual(response.context['total_reports_per_hour'], 4)
        self.assertContains(response, self.entries_fmt % 4)
        response_buckets = response.context['frequentBuckets']
        self.assertEqual(len(response_buckets), 1)
        self.assertEqual(response_buckets[0], bucket)
        self.assertEqual(response_buckets[0].rph, 2)

    def test_old(self):
        """Insert one crash in the past and check that it is not shown."""
        self.client.login(username='test', password='test')
        crash = self.create_crash(shortSignature="crash #1")
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertEqual(response.context['total_reports_per_hour'], 1)
        self.assertContains(response, self.entries_fmt % 1)
        self.assertEqual(len(response.context['frequentBuckets']), 0)
        crash.created -= datetime.timedelta(hours=1, seconds=1)
        crash.save()
        response = self.client.get(reverse(self.name))
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertEqual(response.context['total_reports_per_hour'], 0)
        self.assertContains(response, self.entries_fmt % 0)
        self.assertEqual(len(response.context['frequentBuckets']), 0)
