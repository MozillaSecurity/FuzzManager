"""Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
import logging

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile

from reportmanager.models import (
    OS,
    Bucket,
    BucketWatch,
    Bug,
    BugProvider,
    BugzillaTemplate,
    BugzillaTemplateMode,
    Client,
    Platform,
    Product,
    ReportEntry,
)
from reportmanager.models import TestCase as cmTestCase
from reportmanager.models import Tool
from reportmanager.models import User as cmUser

LOG = logging.getLogger("fm.reportmanager.tests")


def _create_user(
    username,
    email="test@mozilla.com",
    password="test",
    restricted=False,
    permissions=("view_reportmanager", "reportmanager_all"),
):
    user = User.objects.create_user(username, email, password)
    user.user_permissions.clear()
    if permissions:
        content_type = ContentType.objects.get_for_model(cmUser)
        for perm_name in permissions:
            perm = Permission.objects.get(
                content_type=content_type,
                codename=perm_name,
            )
            user.user_permissions.add(perm)
    (user, _) = cmUser.get_or_create_restricted(user)
    user.restricted = restricted
    user.save()
    return user.user


@pytest.fixture
def reportmanager_test(db):  # pylint: disable=invalid-name,unused-argument
    """Common testcase class for all reportmanager unittests"""
    # Create one unrestricted and one restricted test user
    _create_user("test")
    _create_user("test-restricted", restricted=True)
    _create_user("test-noperm", permissions=None)


@pytest.fixture
def user_normal(db, api_client):  # pylint: disable=invalid-name,unused-argument
    """Create a normal, authenticated user"""
    user = _create_user("test")
    api_client.force_authenticate(user=user)
    return user


@pytest.fixture
def user_restricted(db, api_client):  # pylint: disable=invalid-name,unused-argument
    """Create a restricted, authenticated user"""
    user = _create_user("test-restricted", restricted=True)
    api_client.force_authenticate(user=user)
    return user


@pytest.fixture
def user_noperm(db, api_client):  # pylint: disable=invalid-name,unused-argument
    """Create an authenticated user with no reportmanager ACL"""
    user = _create_user("test-noperm", permissions=None)
    api_client.force_authenticate(user=user)
    return user


@pytest.fixture
def user_only_sigs(db, api_client):  # pylint: disable=invalid-name,unused-argument
    """Create an authenticated user with only permission for signatures.zip"""
    user = _create_user(
        "test-only-sigs",
        permissions=("view_reportmanager", "reportmanager_download_signatures"),
    )
    api_client.force_authenticate(user=user)
    return user


@pytest.fixture
def user_only_report(db, api_client):  # pylint: disable=invalid-name,unused-argument
    """Create an authenticated user with only permission for reporting reports"""
    user = _create_user(
        "test-only-report",
        permissions=("view_reportmanager", "reportmanager_report_reports"),
    )
    api_client.force_authenticate(user=user)
    return user


@pytest.fixture
def user(request):
    assert request.param in {
        "normal",
        "restricted",
        "noperm",
        "only_report",
        "only_sigs",
    }
    return request.getfixturevalue(f"user_{request.param}")


@pytest.fixture
def cm():
    class _cm_result:  # pylint: disable=invalid-name
        @staticmethod
        def create_report(
            tool="testtool",
            platform="testplatform",
            product="testproduct",
            product_version=None,
            os="testos",
            testcase=None,
            client="testclient",
            bucket=None,
            stdout="",
            stderr="",
            reportdata="",
            metadata="",
            env="",
            args="",
            reportAddress="",
            reportAddressNumeric=None,
            shortSignature="",
            cachedReportInfo="",
            triagedOnce=False,
        ):
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
            result = ReportEntry.objects.create(
                tool=tool,
                platform=platform,
                product=product,
                os=os,
                testcase=testcase,
                client=client,
                bucket=bucket,
                rawStdout=stdout,
                rawStderr=stderr,
                rawReportData=reportdata,
                metadata=metadata,
                env=env,
                args=args,
                reportAddress=reportAddress,
                reportAddressNumeric=reportAddressNumeric,
                shortSignature=shortSignature,
                cachedReportInfo=cachedReportInfo,
                triagedOnce=triagedOnce,
            )
            LOG.debug("Created ReportEntry pk=%d", result.pk)
            return result

        @staticmethod
        def create_bugprovider(
            classname="BugzillaProvider", hostname="", urlTemplate="%s"
        ):
            result = BugProvider.objects.create(
                classname=classname, hostname=hostname, urlTemplate=urlTemplate
            )
            LOG.debug("Created BugProvider pk=%d", result.pk)
            return result

        @classmethod
        def create_bug(cls, externalId, externalType=None, closed=None):
            if externalType is None:
                externalType = cls.create_bugprovider()
            result = Bug.objects.create(
                externalId=externalId, externalType=externalType, closed=closed
            )
            LOG.debug("Created Bug pk=%d", result.pk)
            return result

        @staticmethod
        def create_testcase(filename, testdata="", quality=0, isBinary=False):
            result = cmTestCase(quality=quality, isBinary=isBinary, size=len(testdata))
            result.test.save(filename, ContentFile(testdata))
            result.save()
            return result

        @staticmethod
        def create_template(
            mode=BugzillaTemplateMode.Bug,
            name="",
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
            testcase_filename="",
            blocks="",
            dependson="",
        ):
            result = BugzillaTemplate.objects.create(
                mode=mode,
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
                testcase_filename=testcase_filename,
            )
            LOG.debug("Created BugzillaTemplate pk=%d", result.pk)
            return result

        @staticmethod
        def create_bucket(
            bug=None, signature="", shortDescription="", frequent=False, permanent=False
        ):
            result = Bucket.objects.create(
                bug=bug,
                signature=signature,
                shortDescription=shortDescription,
                frequent=frequent,
                permanent=permanent,
            )
            LOG.debug("Created Bucket pk=%d", result.pk)
            return result

        @staticmethod
        def create_toolfilter(tool, user="test"):
            user = User.objects.get(username=user)
            cmuser, _ = cmUser.objects.get_or_create(user=user)
            cmuser.defaultToolsFilter.add(Tool.objects.get(name=tool))

        @staticmethod
        def create_bucketwatch(bucket, report=0):
            user = User.objects.get(username="test")
            cmuser, _ = cmUser.objects.get_or_create(user=user)
            if report:
                report = report.pk
            result = BucketWatch.objects.create(
                bucket=bucket, user=cmuser, lastReport=report
            )
            LOG.debug("Created BucketWatch pk=%d", result.pk)
            return result

    return _cm_result()
