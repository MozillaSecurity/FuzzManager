'''
Tests for crashes/all view.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import httplib
#import logging
import pytest

from django.core.urlresolvers import reverse

from .test_crashes import CrashesViewTests


#log = logging.getLogger("fm.crashmanager.tests.allcrashes")


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
