'''
Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import logging

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Permission
from django.db.migrations.executor import MigrationExecutor
from django.db import connection
from django.test import TestCase as DjangoTestCase

from crashmanager.models import User as CMUser
from ..models import Instance, InstancePool, PoolConfiguration, PoolStatusEntry


log = logging.getLogger("fm.ec2spotmanager.tests")  # pylint: disable=invalid-name


class TestCase(DjangoTestCase):
    """Common testcase class for all server unittests"""

    @classmethod
    def setUpClass(cls):
        """Common setup tasks for all server unittests"""
        super(DjangoTestCase, cls).setUpClass()
        user = User.objects.create_user('test', 'test@mozilla.com', 'test')
        user.user_permissions.clear()
        content_type = ContentType.objects.get_for_model(CMUser)
        perm = Permission.objects.get(content_type=content_type, codename='view_ec2spotmanager')
        user.user_permissions.add(perm)
        user = User.objects.create_user('test-noperm', 'test@mozilla.com', 'test')
        user.user_permissions.clear()

    @classmethod
    def tearDownClass(cls):
        """Common teardown tasks for all server unittests"""
        User.objects.get(username='test').delete()
        User.objects.get(username='test-noperm').delete()
        super(DjangoTestCase, cls).tearDownClass()

    @staticmethod
    def create_config(name, parent=None, size=None, cycle_interval=None, ec2_key_name=None, ec2_security_groups=None,
                      ec2_instance_types=None, ec2_image_name=None, userdata_macros=None, ec2_allowed_regions=None,
                      ec2_max_price=None, ec2_tags=None, ec2_raw_config=None):
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
        result.save()
        log.debug("Created PoolConfiguration pk=%d", result.pk)
        return result

    @staticmethod
    def create_pool(config, enabled=False, last_cycled=None):
        result = InstancePool.objects.create(config=config, isEnabled=enabled, last_cycled=last_cycled)
        log.debug("Created InstancePool pk=%d", result.pk)
        return result

    @staticmethod
    def create_poolmsg(pool):
        result = PoolStatusEntry.objects.create(pool=pool, type=0)
        log.debug("Created PoolStatusEntry pk=%d", result.pk)
        return result

    @staticmethod
    def create_instance(hostname,
                        pool=None,
                        status_code=0,
                        status_data=None,
                        ec2_instance_id=None,
                        ec2_region="",
                        ec2_zone=""):
        result = Instance.objects.create(pool=pool, hostname=hostname, status_code=status_code, status_data=status_data,
                                         instance_id=ec2_instance_id, region=ec2_region, zone=ec2_zone)
        log.debug("Created Instance pk=%d", result.pk)
        return result


class TestMigrations(TestCase):
    '''
    source: https://www.caktusgroup.com/blog/2016/02/02/writing-unit-tests-django-migrations/
    '''

    @property
    def app(self):
        return apps.get_containing_app_config(type(self).__module__).name

    migrate_from = None
    migrate_to = None

    def setUp(self):
        assert self.migrate_from and self.migrate_to, \
            "TestCase '{}' must define migrate_from and migrate_to properties".format(type(self).__name__)
        self.migrate_from = [(self.app, self.migrate_from)]
        self.migrate_to = [(self.app, self.migrate_to)]
        executor = MigrationExecutor(connection)
        old_apps = executor.loader.project_state(self.migrate_from).apps

        # Reverse to the original migration
        executor.migrate(self.migrate_from)

        self.setUpBeforeMigration(old_apps)

        # Run the migration to test
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()  # reload.
        executor.migrate(self.migrate_to)

        self.apps = executor.loader.project_state(self.migrate_to).apps

    def setUpBeforeMigration(self, apps):
        pass
