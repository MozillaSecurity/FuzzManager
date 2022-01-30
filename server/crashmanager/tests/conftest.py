# coding: utf-8
'''Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

from __future__ import annotations

import logging
from typing import cast

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Permission
from django.core.files.base import ContentFile
import pytest
from rest_framework.test import APIClient
from crashmanager.models import Bucket, BucketWatch, Bug, BugProvider, BugzillaTemplate, BugzillaTemplateMode, Client, \
    CrashEntry, OS, Platform, Product, TestCase as cmTestCase, Tool, User as cmUser


LOG = logging.getLogger("fm.crashmanager.tests")


def _create_user(username: str, email: str = "test@mozilla.com", password: str = "test", restricted: bool = False, has_permission: bool = True) -> User:
    user = User.objects.create_user(username, email, password)
    user.user_permissions.clear()
    if has_permission:
        content_type = ContentType.objects.get_for_model(cmUser)
        perm = Permission.objects.get(content_type=content_type, codename='view_crashmanager')
        user.user_permissions.add(perm)
    (user, _) = cmUser.get_or_create_restricted(user)
    user.restricted = restricted
    user.save()
    return user.user


@pytest.fixture
def crashmanager_test(db: str) -> None:  # pylint: disable=invalid-name,unused-argument
    """Common testcase class for all crashmanager unittests"""
    # Create one unrestricted and one restricted test user
    _create_user("test")
    _create_user("test-restricted", restricted=True)
    _create_user("test-noperm", has_permission=False)


@pytest.fixture
def user_normal(db: str, api_client: APIClient) -> User:  # pylint: disable=invalid-name,unused-argument
    """Create a normal, authenticated user"""
    user = _create_user("test")
    api_client.force_authenticate(user=user)
    return user


@pytest.fixture
def user_restricted(db: str, api_client: APIClient) -> User:  # pylint: disable=invalid-name,unused-argument
    """Create a restricted, authenticated user"""
    user = _create_user("test-restricted", restricted=True)
    api_client.force_authenticate(user=user)
    return user


@pytest.fixture
def user_noperm(db: str, api_client: APIClient) -> User:  # pylint: disable=invalid-name,unused-argument
    """Create an authenticated user with no crashmanager ACL"""
    user = _create_user("test-noperm", has_permission=False)
    api_client.force_authenticate(user=user)
    return user


@pytest.fixture
def user(request):
    assert request.param in {"normal", "restricted", "noperm"}
    return request.getfixturevalue("user_" + request.param)


@pytest.fixture
def cm():

    class _cm_result(object):  # pylint: disable=invalid-name

        @staticmethod
        def create_crash(tool: str = "testtool",
                         platform: str = "testplatform",
                         product: str = "testproduct",
                         product_version: Product | None = None,
                         os: str = "testos",
                         testcase: cmTestCase | None = None,
                         client: str = "testclient",
                         bucket: Bucket | None = None,
                         stdout: str = "",
                         stderr: str = "",
                         crashdata: str = "",
                         metadata: str = "",
                         env: str = "",
                         args: str = "",
                         crashAddress: str = "",
                         crashAddressNumeric: int | None = None,
                         shortSignature: str = "",
                         cachedCrashInfo: str = "",
                         triagedOnce: bool = False) -> CrashEntry:
            # create tool
            tool, created = Tool.objects.get_or_create(name=tool)
            assert isinstance(tool, Tool)
            if created:
                LOG.debug("Created Tool pk=%d", tool.pk)
            # create platform
            platform, created = Platform.objects.get_or_create(name=platform)
            assert isinstance(platform, Platform)
            if created:
                LOG.debug("Created Platform pk=%d", platform.pk)
            # create product
            product, created = Product.objects.get_or_create(name=product)
            assert isinstance(product, Product)
            if created:
                LOG.debug("Created Product pk=%d", product.pk)
            if product_version is not None:
                product.version = str(product_version)
                product.save()
            # create os
            os, created = OS.objects.get_or_create(name=os)
            assert isinstance(os, OS)
            if created:
                LOG.debug("Created OS pk=%d", os.pk)
            # create client
            client, created = Client.objects.get_or_create(name=client)
            assert isinstance(client, Client)
            if created:
                LOG.debug("Created Client pk=%d", client.pk)
            result = cast(CrashEntry, CrashEntry.objects.create(tool=tool,
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
                                                                triagedOnce=triagedOnce))
            LOG.debug("Created CrashEntry pk=%d", result.pk)
            return result

        @staticmethod
        def create_bugprovider(classname: str = "BugzillaProvider", hostname: str = "", urlTemplate: str = "%s") -> BugProvider:
            result = cast(BugProvider, BugProvider.objects.create(classname=classname,
                                                                  hostname=hostname,
                                                                  urlTemplate=urlTemplate))
            LOG.debug("Created BugProvider pk=%d", result.pk)
            return result

        @classmethod
        def create_bug(cls, externalId: str, externalType: BugProvider | None = None, closed: bool | None = None) -> Bug:
            if externalType is None:
                externalType = cls.create_bugprovider()
            result = cast(Bug, Bug.objects.create(externalId=externalId, externalType=externalType, closed=closed))
            LOG.debug("Created Bug pk=%d", result.pk)
            return result

        @staticmethod
        def create_testcase(filename: str,
                            testdata: str = "",
                            quality: int = 0,
                            isBinary: bool = False) -> cmTestCase:
            result = cmTestCase(quality=quality, isBinary=isBinary, size=len(testdata))
            result.test.save(filename, ContentFile(testdata))
            result.save()
            return result

        @staticmethod
        def create_template(mode: str = BugzillaTemplateMode.Bug,
                            name: str = "",
                            product: str = "",
                            component: str = "",
                            summary: str = "",
                            version: str = "",
                            description: str = "",
                            whiteboard: str = "",
                            keywords: str = "",
                            op_sys: str = "",
                            platform: str = "",
                            priority: str = "",
                            severity: str = "",
                            alias: str = "",
                            cc: str = "",
                            assigned_to: str = "",
                            qa_contact: str = "",
                            target_milestone: str = "",
                            attrs: str = "",
                            security: bool = False,
                            security_group: str = "",
                            comment: str = "",
                            testcase_filename: str = "",
                            blocks: str = "",
                            dependson: str = "") -> BugzillaTemplate:
            result = cast(BugzillaTemplate, BugzillaTemplate.objects.create(mode=mode,
                                                                            name=name,
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
                                                                            testcase_filename=testcase_filename))
            LOG.debug("Created BugzillaTemplate pk=%d", result.pk)
            return result

        @staticmethod
        def create_bucket(bug: Bug | None = None,
                          signature: str = "",
                          shortDescription: str = "",
                          frequent: bool = False,
                          permanent: bool = False) -> Bucket:
            result = cast(Bucket, Bucket.objects.create(bug=bug,
                                                        signature=signature,
                                                        shortDescription=shortDescription,
                                                        frequent=frequent,
                                                        permanent=permanent))
            LOG.debug("Created Bucket pk=%d", result.pk)
            return result

        @staticmethod
        def create_toolfilter(tool: str, user: str = 'test') -> None:
            user = User.objects.get(username=user)
            cmuser, _ = cmUser.objects.get_or_create(user=user)
            cmuser.defaultToolsFilter.add(Tool.objects.get(name=tool))

        @staticmethod
        def create_bucketwatch(bucket: Bucket, crash=0) -> BucketWatch:
            user = User.objects.get(username='test')
            cmuser, _ = cmUser.objects.get_or_create(user=user)
            if crash:
                crash = crash.pk
            result = cast(BucketWatch, BucketWatch.objects.create(bucket=bucket, user=cmuser, lastCrash=crash))
            LOG.debug("Created BucketWatch pk=%d", result.pk)
            return result

    return _cm_result()
