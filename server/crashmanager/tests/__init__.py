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

from ..models import Bucket, Bug, BugProvider, Client, CrashEntry, OS, Platform, Product, TestCase as cmTestCase, \
                     Tool, User as cmUser

logging.getLogger("django").setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)
log = logging.getLogger("fm.crashmanager.tests")


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
    def create_bug(externalId, externalType=None, closed=None):
        if externalType is None:
            externalType, _ = \
                BugProvider.objects.get_or_create(classname="BugzillaProvider",
                                                  hostname="bugzilla.mozilla.org",
                                                  urlTemplate="https://bugzilla.mozilla.org/show_bug.cgi?id=%s")
        result = Bug.objects.create(externalId=externalId, externalType=externalType, closed=closed)
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
