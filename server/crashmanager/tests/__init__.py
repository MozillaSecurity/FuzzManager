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
from django.core.files.base import ContentFile
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase as DjangoTestCase
import pytest

from ..models import Bucket, BucketWatch, Bug, BugProvider, BugzillaTemplate, Client, CrashEntry, OS, Platform, \
    Product, TestCase as cmTestCase, Tool, User as cmUser

logging.getLogger("django").setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)


log = logging.getLogger("fm.crashmanager.tests")  # pytest: disable=invalid-name


class TestCase(DjangoTestCase):
    """Common testcase class for all server unittests"""

    @classmethod
    def setUpClass(cls):
        """Common setup tasks for all server unittests"""
        super(DjangoTestCase, cls).setUpClass()

        def create_user(username, email="test@mozilla.com", password="test", restricted=False, has_permission=True):
            user = User.objects.create_user(username, email, password)
            user.user_permissions.clear()
            if has_permission:
                content_type = ContentType.objects.get_for_model(cmUser)
                perm = Permission.objects.get(content_type=content_type, codename='view_crashmanager')
                user.user_permissions.add(perm)
            (user, created) = cmUser.get_or_create_restricted(user)
            user.restricted = restricted
            user.save()
            return user

        # Create one unrestricted and one restricted test user
        create_user("test")
        create_user("test-restricted", restricted=True)
        create_user("test-noperm", has_permission=False)

    @classmethod
    def tearDownClass(cls):
        """Common teardown tasks for all server unittests"""
        User.objects.get(username='test').delete()
        User.objects.get(username='test-restricted').delete()
        User.objects.get(username='test-noperm').delete()
        super(DjangoTestCase, cls).tearDownClass()

    @staticmethod
    def create_crash(tool="testtool",
                     platform="testplatform",
                     product="testproduct",
                     product_version=None,
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
        if product_version is not None:
            product.version = product_version
            product.save()
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
    def create_bugprovider(classname="BugzillaProvider", hostname="", urlTemplate="%s"):
        result = BugProvider.objects.create(classname=classname,
                                            hostname=hostname,
                                            urlTemplate=urlTemplate)
        log.debug("Created BugProvider pk=%d", result.pk)
        return result

    @staticmethod
    def create_bug(externalId, externalType=None, closed=None):
        if externalType is None:
            externalType = TestCase.create_bugprovider()
        result = Bug.objects.create(externalId=externalId, externalType=externalType, closed=closed)
        log.debug("Created Bug pk=%d", result.pk)
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
    def create_template(name="",
                        product="",
                        component="",
                        summary="",
                        version="",
                        description="",
                        whiteboard="",
                        keywords="",
                        op_sys="",
                        platform="",
                        priority="",
                        severity="",
                        alias="",
                        cc="",
                        assigned_to="",
                        qa_contact="",
                        target_milestone="",
                        attrs="",
                        security=False,
                        security_group="",
                        comment="",
                        testcase_filename=""):
        result = BugzillaTemplate.objects.create(name=name,
                                                 product=product,
                                                 component=component,
                                                 summary=summary,
                                                 version=version,
                                                 description=description,
                                                 whiteboard=whiteboard,
                                                 keywords=keywords,
                                                 op_sys=op_sys,
                                                 platform=platform,
                                                 priority=priority,
                                                 severity=severity,
                                                 alias=alias,
                                                 cc=cc,
                                                 assigned_to=assigned_to,
                                                 qa_contact=qa_contact,
                                                 target_milestone=target_milestone,
                                                 attrs=attrs,
                                                 security=security,
                                                 security_group=security_group,
                                                 comment=comment,
                                                 testcase_filename=testcase_filename)
        log.debug("Created BugzillaTemplate pk=%d", result.pk)
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

    @staticmethod
    def create_bucketwatch(bucket, crash=0):
        user = User.objects.get(username='test')
        cmuser, _ = cmUser.objects.get_or_create(user=user)
        if crash:
            crash = crash.pk
        result = BucketWatch.objects.create(bucket=bucket, user=cmuser, lastCrash=crash)
        log.debug("Created BucketWatch pk=%d", result.pk)
        return result


@pytest.fixture
def migration_hook(request):
    '''
    Pause migration at the migration named in @pytest.mark.migrate_from('0001-initial-migration')

    The migration_hook param will be a callable to then trigger the migration named in:
        @pytest.mark.migrate_from('0002-migrate-things')

    migration_hook also has an 'apps' attribute which is used to lookup models in the current migration state

    eg.
        MyModel = migration_hook.apps.get_model('myapp', 'MyModel')

    based on: https://www.caktusgroup.com/blog/2016/02/02/writing-unit-tests-django-migrations/
    '''
    assert 'migrate_from' in request.keywords, 'must mark the migration to stop at with @pytest.mark.migrate_from()'
    assert len(request.keywords['migrate_from'].args) == 1, 'migrate_from mark expects 1 arg'
    assert not request.keywords['migrate_from'].kwargs, 'migrate_from mark takes no keywords'
    assert 'migrate_to' in request.keywords, 'must mark the migration to hook with @pytest.mark.migrate_to()'
    assert len(request.keywords['migrate_to'].args) == 1, 'migrate_to mark expects 1 arg'
    assert not request.keywords['migrate_to'].kwargs, 'migrate_to mark takes no keywords'

    app = apps.get_containing_app_config(request.module.__name__).name

    migrate_from = [(app, request.keywords['migrate_from'].args[0])]
    migrate_to = [(app, request.keywords['migrate_to'].args[0])]

    class migration_hook_result(object):

        def __init__(self, _from, _to):
            self._to = _to
            executor = MigrationExecutor(connection)
            self.apps = executor.loader.project_state(_from).apps

            # Reverse to the original migration
            executor.migrate(_from)

        def __call__(self):
            # Run the migration to test
            executor = MigrationExecutor(connection)
            executor.loader.build_graph()  # reload.
            executor.migrate(self._to)

            self.apps = executor.loader.project_state(self._to).apps

    yield migration_hook_result(migrate_from, migrate_to)
