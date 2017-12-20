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
        User.objects.create_user('test', 'test@mozilla.com', 'test')

    @classmethod
    def tearDownClass(cls):
        """Common teardown tasks for all server unittests"""
        User.objects.get(username='test').delete()
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
