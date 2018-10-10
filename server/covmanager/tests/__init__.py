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

from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from django.test import TestCase as DjangoTestCase
import pytest

from crashmanager.models import Client, Tool, User as cmUser
from ..models import Collection, CollectionFile, Repository


log = logging.getLogger("fm.covmanager.tests")  # pylint: disable=invalid-name


def _check_hg():
    try:
        proc = subprocess.Popen(["hg"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = proc.communicate()
        if output and proc.wait() == 0:
            return True
    except OSError:  # FileNotFoundError
        pass
    return False


HAVE_HG = _check_hg()


def _check_git():
    try:
        proc = subprocess.Popen(["git"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = proc.communicate()
        if output and proc.wait() == 1:
            return True
    except OSError:  # FileNotFoundError
        pass
    return False


HAVE_GIT = _check_git()


class TestCase(DjangoTestCase):
    """Common testcase class for all server unittests"""

    @classmethod
    def setUpClass(cls):
        """Common setup tasks for all server unittests"""
        super(DjangoTestCase, cls).setUpClass()
        user = User.objects.create_user('test', 'test@mozilla.com', 'test')
        user.user_permissions.clear()
        content_type = ContentType.objects.get_for_model(cmUser)
        perm = Permission.objects.get(content_type=content_type, codename='view_covmanager')
        user.user_permissions.add(perm)
        user = User.objects.create_user('test-noperm', 'test@mozilla.com', 'test')
        user.user_permissions.clear()

    @classmethod
    def tearDownClass(cls):
        """Common teardown tasks for all server unittests"""
        User.objects.get(username='test').delete()
        User.objects.get(username='test-noperm').delete()
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
        location = self.mkdtemp(prefix='testrepo', dir=os.path.dirname(__file__))
        if repotype == "git":
            if not HAVE_GIT:
                pytest.skip("git is not available")
            classname = "GITSourceCodeProvider"
        elif repotype == "hg":
            if not HAVE_GIT:
                pytest.skip("hg is not available")
            classname = "HGSourceCodeProvider"
        else:
            raise Exception("unknown repository type: %s (expecting git or hg)" % repotype)
        result = Repository.objects.create(classname=classname, name=name, location=location)
        log.debug("Created Repository pk=%d", result.pk)
        if repotype == "git":
            self.git(result, "init")
        elif repotype == "hg":
            self.hg(result, "init")
        return result

    def hg(self, repo, *args):
        path = os.getcwd()
        try:
            os.chdir(repo.location)
            return subprocess.check_output(["hg"] + list(args)).decode("utf-8")
        finally:
            os.chdir(path)

    def git(self, repo, *args):
        path = os.getcwd()
        try:
            os.chdir(repo.location)
            return subprocess.check_output(["git"] + list(args)).decode("utf-8")
        finally:
            os.chdir(path)

    def create_collection_file(self, data):
        location = self.mkdtemp(prefix='testcov_', dir=os.path.dirname(__file__))
        path = self.mkstemp(suffix=".data", dir=location)
        with open(path, "w") as fp:
            fp.write(data)
        result = CollectionFile.objects.create(file=File(open(path)))
        log.debug("Created CollectionFile pk=%d", result.pk)
        return result

    def create_collection(self,
                          created=None,
                          description="",
                          repository=None,
                          revision="",
                          branch="",
                          tools=("testtool",),
                          client="testclient",
                          coverage='{"linesTotal":0,'
                                   '"name":null,'
                                   '"coveragePercent":0.0,'
                                   '"children":{},'
                                   '"linesMissed":0,'
                                   '"linesCovered":0}'):
        # create collectionfile
        coverage = self.create_collection_file(coverage)
        # create client
        client, created = Client.objects.get_or_create(name=client)
        if created:
            log.debug("Created Client pk=%d", client.pk)
        # create repository
        if repository is None:
            repository = self.create_repository("git")
        result = Collection.objects.create(description=description,
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
