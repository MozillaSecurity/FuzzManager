# coding: utf-8
'''Common test fixtures

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
import pytest
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files import File
from covmanager.models import Collection, CollectionFile, Repository
from crashmanager.models import Client, Tool, User as cmUser


LOG = logging.getLogger("fm.covmanager.tests")


def _check_git():
    try:
        proc = subprocess.Popen(["git"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = proc.communicate()
        if output and proc.wait() == 1:
            return True
    except OSError:  # FileNotFoundError
        pass
    return False


def _check_hg():
    try:
        proc = subprocess.Popen(["hg"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        output = proc.communicate()
        if output and proc.wait() == 0:
            return True
    except OSError:  # FileNotFoundError
        pass
    return False


HAVE_GIT = _check_git()
HAVE_HG = _check_hg()


@pytest.fixture
def covmanager_test(db):  # pylint: disable=invalid-name,unused-argument
    """Common setup/teardown tasks for all server unittests"""
    user = User.objects.create_user('test', 'test@mozilla.com', 'test')
    user.user_permissions.clear()
    content_type = ContentType.objects.get_for_model(cmUser)
    perm = Permission.objects.get(content_type=content_type, codename='view_covmanager')
    user.user_permissions.add(perm)
    user_np = User.objects.create_user('test-noperm', 'test@mozilla.com', 'test')
    user_np.user_permissions.clear()


@pytest.fixture
def cm(request):

    class _result(object):
        have_git = HAVE_GIT
        have_hg = HAVE_HG

        @classmethod
        def create_repository(cls, repotype, name="testrepo"):
            location = tempfile.mkdtemp(prefix='testrepo', dir=os.path.dirname(__file__))
            request.addfinalizer(lambda: shutil.rmtree(location))
            if repotype == "git":
                if not HAVE_GIT:
                    pytest.skip("git is not available")
                classname = "GITSourceCodeProvider"
            elif repotype == "hg":
                if not HAVE_HG:
                    pytest.skip("hg is not available")
                classname = "HGSourceCodeProvider"
            else:
                raise Exception("unknown repository type: %s (expecting git or hg)" % repotype)
            result = Repository.objects.create(classname=classname, name=name, location=location)
            LOG.debug("Created Repository pk=%d", result.pk)
            if repotype == "git":
                cls.git(result, "init")
            elif repotype == "hg":
                cls.hg(result, "init")
            return result

        @staticmethod
        def create_collection_file(data):
            location = tempfile.mkdtemp(prefix='testcov_', dir=os.path.dirname(__file__))
            request.addfinalizer(lambda: shutil.rmtree(location))
            tmp_fd, path = tempfile.mkstemp(suffix=".data", dir=location)
            os.close(tmp_fd)
            with open(path, "w") as fp:
                fp.write(data)
            result = CollectionFile.objects.create(file=File(open(path)))
            LOG.debug("Created CollectionFile pk=%d", result.pk)
            return result

        @classmethod
        def create_collection(cls,
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
            coverage = cls.create_collection_file(coverage)
            # create client
            client, created = Client.objects.get_or_create(name=client)
            if created:
                LOG.debug("Created Client pk=%d", client.pk)
            # create repository
            if repository is None:
                repository = cls.create_repository("git")
            result = Collection.objects.create(description=description,
                                               repository=repository,
                                               revision=revision,
                                               branch=branch,
                                               client=client,
                                               coverage=coverage)
            LOG.debug("Created Collection pk=%d", result.pk)
            # create tools
            for tool in tools:
                tool, created = Tool.objects.get_or_create(name=tool)
                if created:
                    LOG.debug("Created Tool pk=%d", tool.pk)
                result.tools.add(tool)
            return result

        @staticmethod
        def git(repo, *args):
            path = os.getcwd()
            try:
                os.chdir(repo.location)
                return subprocess.check_output(["git"] + list(args)).decode("utf-8")
            finally:
                os.chdir(path)

        @staticmethod
        def hg(repo, *args):
            path = os.getcwd()
            try:
                os.chdir(repo.location)
                return subprocess.check_output(["hg"] + list(args)).decode("utf-8")
            finally:
                os.chdir(path)

    return _result()
