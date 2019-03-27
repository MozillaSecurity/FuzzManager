# coding: utf-8
'''Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import logging
from django.core.files.base import ContentFile
from django.test import SimpleTestCase as DjangoTestCase
from django.utils import timezone
from ec2spotmanager.models import Instance, InstancePool, PoolConfiguration, PoolStatusEntry


LOG = logging.getLogger("fm.ec2spotmanager.tests")  # pylint: disable=invalid-name


def assert_contains(response, text):
    """Assert that the response was successful, and contains the given text.
    """

    class _(DjangoTestCase):

        def runTest(self):
            pass

    _().assertContains(response, text)


def create_config(name, parent=None, size=None, cycle_interval=None, ec2_key_name=None, ec2_security_groups=None,
                  ec2_instance_types=None, ec2_image_name=None, userdata_macros=None, ec2_allowed_regions=None,
                  ec2_max_price=None, ec2_tags=None, ec2_raw_config=None, userdata=None):
    result = PoolConfiguration.objects.create(name=name, parent=parent, size=size, cycle_interval=cycle_interval,
                                              ec2_key_name=ec2_key_name,
                                              ec2_image_name=ec2_image_name,
                                              ec2_max_price=ec2_max_price)
    if ec2_security_groups is not None:
        result.ec2_security_groups_list = ec2_security_groups
    if ec2_instance_types is not None:
        result.ec2_instance_types_list = ec2_instance_types
    if ec2_allowed_regions is not None:
        result.ec2_allowed_regions_list = ec2_allowed_regions
    if userdata_macros is not None:
        result.userdata_macros_dict = userdata_macros
    if ec2_tags is not None:
        result.ec2_tags_dict = ec2_tags
    if ec2_raw_config is not None:
        result.ec2_raw_config_dict = ec2_raw_config
    if userdata is not None:
        if not result.userdata_file.name:
            result.userdata_file.save("default.sh", ContentFile(""))
        result.userdata = userdata
    result.storeTestAndSave()
    LOG.debug("Created PoolConfiguration pk=%d", result.pk)
    return result


def create_pool(config, enabled=False, last_cycled=None):
    result = InstancePool.objects.create(config=config, isEnabled=enabled, last_cycled=last_cycled)
    LOG.debug("Created InstancePool pk=%d", result.pk)
    return result


def create_poolmsg(pool):
    result = PoolStatusEntry.objects.create(pool=pool, type=0)
    LOG.debug("Created PoolStatusEntry pk=%d", result.pk)
    return result


def create_instance(hostname,
                    pool=None,
                    status_code=0,
                    status_data=None,
                    ec2_instance_id=None,
                    ec2_region="",
                    ec2_zone="",
                    size=1,
                    created=None):
    if created is None:
        created = timezone.now()
    result = Instance.objects.create(pool=pool, hostname=hostname, status_code=status_code, status_data=status_data,
                                     instance_id=ec2_instance_id, region=ec2_region, zone=ec2_zone, size=size,
                                     created=created)
    LOG.debug("Created Instance pk=%d", result.pk)
    return result
