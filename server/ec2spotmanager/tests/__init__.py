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


class UncatchableException(BaseException):
    """Exception that does not inherit from Exception, so will not be caught by normal exception handling."""
    pass


def assert_contains(response, text):
    """Assert that the response was successful, and contains the given text.
    """

    class _(DjangoTestCase):

        def runTest(self):
            pass

    _().assertContains(response, text)


def create_config(name, parent=None, size=None, cycle_interval=None, ec2_key_name=None, ec2_security_groups=None,
                  ec2_instance_types=None, ec2_image_name=None, ec2_userdata_macros=None, ec2_allowed_regions=None,
                  max_price=None, instance_tags=None, ec2_raw_config=None, ec2_userdata=None, gce_image_name=None,
                  gce_container_name=None, gce_disk_size=None):
    result = PoolConfiguration.objects.create(name=name, parent=parent, size=size, cycle_interval=cycle_interval,
                                              ec2_key_name=ec2_key_name,
                                              ec2_image_name=ec2_image_name,
                                              max_price=max_price,
                                              gce_image_name=gce_image_name,
                                              gce_disk_size=gce_disk_size,
                                              gce_container_name=gce_container_name)
    if ec2_security_groups is not None:
        result.ec2_security_groups_list = ec2_security_groups
    if ec2_instance_types is not None:
        result.ec2_instance_types_list = ec2_instance_types
    if ec2_allowed_regions is not None:
        result.ec2_allowed_regions_list = ec2_allowed_regions
    if ec2_userdata_macros is not None:
        result.ec2_userdata_macros_dict = ec2_userdata_macros
    if instance_tags is not None:
        result.instance_tags_dict = instance_tags
    if ec2_raw_config is not None:
        result.ec2_raw_config_dict = ec2_raw_config
    if ec2_userdata is not None:
        if not result.ec2_userdata_file.name:
            result.ec2_userdata_file.save("default.sh", ContentFile(""))
        result.ec2_userdata = ec2_userdata
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
                    created=None,
                    provider='EC2Spot'):
    if created is None:
        created = timezone.now()
    result = Instance.objects.create(pool=pool, hostname=hostname, status_code=status_code, status_data=status_data,
                                     instance_id=ec2_instance_id, region=ec2_region, zone=ec2_zone, size=size,
                                     created=created, provider=provider)
    LOG.debug("Created Instance pk=%d", result.pk)
    return result
