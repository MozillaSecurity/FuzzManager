'''
Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import logging

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.test import TestCase as DjangoTestCase

from ..models import PoolConfiguration


log = logging.getLogger("fm.ec2spotmanager.tests")


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

    @staticmethod
    def create_config(name, parent=None, size=None, cycle_interval=None, aws_access_key_id=None,
                      aws_secret_access_key=None, ec2_key_name=None, ec2_security_groups=None, ec2_instance_type=None,
                      ec2_image_name=None, ec2_userdata_macros=None, ec2_allowed_regions=None,
                      ec2_max_price=None, ec2_tags=None, ec2_raw_config=None):
        result = PoolConfiguration.objects.create(name=name, parent=parent, size=size, cycle_interval=cycle_interval,
                                                  aws_access_key_id=aws_access_key_id,
                                                  aws_secret_access_key=aws_secret_access_key,
                                                  ec2_key_name=ec2_key_name,
                                                  ec2_instance_type=ec2_instance_type,
                                                  ec2_image_name=ec2_image_name,
                                                  ec2_max_price=ec2_max_price)
        if ec2_security_groups is not None:
            result.ec2_security_groups_list = ec2_security_groups
        if ec2_allowed_regions is not None:
            result.ec2_allowed_regions_list = ec2_allowed_regions
        if ec2_userdata_macros is not None:
            result.ec2_userdata_macros_dict = ec2_userdata_macros
        if ec2_tags is not None:
            result.ec2_tags_dict = ec2_tags
        if ec2_raw_config is not None:
            result.ec2_raw_config_dict = ec2_raw_config
        result.save()
        log.debug("Created PoolConfiguration pk=%d", result.pk)
        return result
