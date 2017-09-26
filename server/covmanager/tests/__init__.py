'''
Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import logging
import os
import shutil
import subprocess
import tempfile

from django.contrib.auth.models import User
from django.core.files import File
from django.test import TestCase as DjangoTestCase

from crashmanager.models import Client, Tool
from ..models import Collection, CollectionFile, Repository


log = logging.getLogger("fm.covmanager.tests")


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

    def mkdtemp(self, *args, **kwds):
        path = tempfile.mkdtemp(*args, **kwds)
        self.addCleanup(shutil.rmtree, path)
        return path

    def mkstemp(self, *args, **kwds):
        tmp_fd, path = tempfile.mkstemp(*args, **kwds)
        os.close(tmp_fd)
        self.addCleanup(os.unlink, path)
        return path

    def create_repository(self, repotype, name="testrepo"):
        location = self.mkdtemp()
        if repotype == "git":
            classname = "GITSourceCodeProvider"
        elif repotype == "hg":
            classname = "HGSourceCodeProvider"
        else:
            raise Exception("unknown repository type: %s (expecting git or hg)" % repotype)
        result = Repository.objects.create(classname=classname, name=name, location=location)
        log.debug("Created Repository pk=%d", result.pk)
        return result

    def create_collection(self,
                          created=None,
                          description="",
                          repository=None,
                          revision="",
                          branch="",
                          tools=("testtool",),
                          client="testclient",
                          coverage=None):
        # create collectionfile
        coverage = CollectionFile.objects.create(file=File(coverage))
        log.debug("Created CollectionFile pk=%d", coverage.pk)
        # create client
        client, created = Client.objects.get_or_create(name=client)
        if created:
            log.debug("Created Client pk=%d", client.pk)
        # create repository
        if repository is None:
            repository = self.create_repository("git")
        result = Collection.objects.create(#created=created,
                                           description=description,
                                           repository=repository,
                                           revision=revision,
                                           branch=branch,
                                           client=client,
                                           coverage=coverage)
        log.debug("Created Collection pk=%d", result.pk)
        # create tools
        for tool in tools:
            tool, created = Tool.objects.get_or_create(name=tool)
            if created:
                log.debug("Created Tool pk=%d", tool.pk)
            result.tools.add(tool)
        return result
