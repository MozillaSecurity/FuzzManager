'''
Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import logging

from django.test import TestCase as DjangoTestCase
from django.contrib.auth.models import User


logging.getLogger("django").setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)


class TestCase(DjangoTestCase):
    """Common testcase class for all server unittests"""

    @classmethod
    def setUpClass(cls):
        """Common setup tasks for all server unittests"""
        super(DjangoTestCase, cls).setUpClass()
        User.objects.create_user('test', 'test@mozilla.com', 'test')

    @classmethod
    def tearDownClass(cls):
        """Common teardown tasks for all server unittests"""
        User.objects.get(username='test').delete()
        super(DjangoTestCase, cls).tearDownClass()
