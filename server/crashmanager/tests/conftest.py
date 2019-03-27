# coding: utf-8
'''Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import logging
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Permission
from django.core.files.base import ContentFile
import pytest
from crashmanager.models import Bucket, BucketWatch, Bug, BugProvider, BugzillaTemplate, Client, CrashEntry, OS, \
    Platform, Product, TestCase as cmTestCase, Tool, User as cmUser


LOG = logging.getLogger("fm.crashmanager.tests")


def _create_user(username, email="test@mozilla.com", password="test", restricted=False, has_permission=True):
    user = User.objects.create_user(username, email, password)
    user.user_permissions.clear()
    if has_permission:
        content_type = ContentType.objects.get_for_model(cmUser)
        perm = Permission.objects.get(content_type=content_type, codename='view_crashmanager')
        user.user_permissions.add(perm)
    (user, _) = cmUser.get_or_create_restricted(user)
    user.restricted = restricted
    user.save()
    return user


@pytest.fixture
def crashmanager_test(db):  # pylint: disable=invalid-name,unused-argument
    """Common testcase class for all crashmanager unittests"""
    # Create one unrestricted and one restricted test user
    _create_user("test")
    _create_user("test-restricted", restricted=True)
    _create_user("test-noperm", has_permission=False)


@pytest.fixture
def cm():

    class _cm_result(object):  # pylint: disable=invalid-name

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
                LOG.debug("Created Tool pk=%d", tool.pk)
            # create platform
            platform, created = Platform.objects.get_or_create(name=platform)
            if created:
                LOG.debug("Created Platform pk=%d", platform.pk)
            # create product
            product, created = Product.objects.get_or_create(name=product)
            if created:
                LOG.debug("Created Product pk=%d", product.pk)
            if product_version is not None:
                product.version = product_version
                product.save()
            # create os
            os, created = OS.objects.get_or_create(name=os)
            if created:
                LOG.debug("Created OS pk=%d", os.pk)
            # create client
            client, created = Client.objects.get_or_create(name=client)
            if created:
                LOG.debug("Created Client pk=%d", client.pk)
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
            LOG.debug("Created CrashEntry pk=%d", result.pk)
            return result

        @staticmethod
        def create_bugprovider(classname="BugzillaProvider", hostname="", urlTemplate="%s"):
            result = BugProvider.objects.create(classname=classname,
                                                hostname=hostname,
                                                urlTemplate=urlTemplate)
            LOG.debug("Created BugProvider pk=%d", result.pk)
            return result

        @classmethod
        def create_bug(cls, externalId, externalType=None, closed=None):
            if externalType is None:
                externalType = cls.create_bugprovider()
            result = Bug.objects.create(externalId=externalId, externalType=externalType, closed=closed)
            LOG.debug("Created Bug pk=%d", result.pk)
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
            LOG.debug("Created BugzillaTemplate pk=%d", result.pk)
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
            LOG.debug("Created Bucket pk=%d", result.pk)
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
            LOG.debug("Created BucketWatch pk=%d", result.pk)
            return result

    return _cm_result()
