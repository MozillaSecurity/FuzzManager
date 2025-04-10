"""Common test fixtures

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import logging
import os
import shutil
import subprocess
import tempfile

import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType

from covmanager.models import Collection, CollectionFile, Repository
from crashmanager.models import Client, Tool
from crashmanager.models import User as cmUser
from crashmanager.tests.conftest import _create_user

LOG = logging.getLogger("fm.covmanager.tests")


def _check_git():
    try:
        proc = subprocess.Popen(
            ["git"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        output = proc.communicate()
        if output and proc.wait() == 1:
            return True
    except OSError:  # FileNotFoundError
        pass
    return False


def _check_hg():
    try:
        proc = subprocess.Popen(
            ["hg"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        output = proc.communicate()
        if output and proc.wait() == 0:
            return True
    except OSError:  # FileNotFoundError
        pass
    return False


HAVE_GIT = _check_git()
HAVE_HG = _check_hg()


def _covmgr_create_user(
    username,
    email="test@mozilla.com",
    password="test",
    restricted=False,
    permissions=("view_covmanager", "covmanager_all", "covmanager_submit_collection"),
):
    return _create_user(username, email, password, restricted, permissions)


@pytest.fixture
def covmanager_test(db):  # pylint: disable=invalid-name,unused-argument
    """Common setup/teardown tasks for all server unittests"""
    user = User.objects.create_user("test", "test@mozilla.com", "test")
    user.user_permissions.clear()
    content_type = ContentType.objects.get_for_model(cmUser)
    perm = Permission.objects.get(content_type=content_type, codename="view_covmanager")
    user.user_permissions.add(perm)
    perm = Permission.objects.get(content_type=content_type, codename="covmanager_all")
    user.user_permissions.add(perm)
    user_np = User.objects.create_user("test-noperm", "test@mozilla.com", "test")
    user_np.user_permissions.clear()
    user_ro = User.objects.create_user("test-only-report", "test@mozilla.com", "test")
    user_ro.user_permissions.clear()
    perm = Permission.objects.get(content_type=content_type, codename="view_covmanager")
    user_ro.user_permissions.add(perm)
    perm = Permission.objects.get(
        content_type=content_type, codename="covmanager_submit_collection"
    )
    user_ro.user_permissions.add(perm)


@pytest.fixture
def covmgr_user_normal(db, api_client):  # pylint: disable=invalid-name,unused-argument
    """Create a normal, authenticated user for covmanager tests"""
    user = _covmgr_create_user("test")
    api_client.force_authenticate(user=user)
    return user


@pytest.fixture
def covmgr_user_restricted(
    db, api_client
):  # pylint: disable=invalid-name,unused-argument
    """Create a restricted, authenticated user for covmanager tests"""
    user = _covmgr_create_user("test-restricted", restricted=True)
    api_client.force_authenticate(user=user)
    return user


@pytest.fixture
def covmgr_helper(request, settings, tmpdir):
    class _result:
        have_git = HAVE_GIT
        have_hg = HAVE_HG

        @classmethod
        def create_repository(cls, repotype, name="testrepo"):
            location = tempfile.mkdtemp(
                prefix="testrepo", dir=os.path.dirname(__file__)
            )
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
                raise Exception(
                    f"unknown repository type: {repotype} (expecting git or hg)"
                )
            result = Repository.objects.create(
                classname=classname, name=name, location=location
            )
            LOG.debug("Created Repository pk=%d", result.pk)
            if repotype == "git":
                cls.git(result, "init")
            elif repotype == "hg":
                cls.hg(result, "init")
            return result

        @staticmethod
        def create_collection_file(data):
            # Use a specific temporary directory to upload covmanager files.  This is
            # required as Django now needs a path relative to that folder in FileField
            location = str(tmpdir)
            CollectionFile.file.field.storage.location = location

            tmp_fd, path = tempfile.mkstemp(suffix=".data", dir=location)
            os.close(tmp_fd)
            with open(path, "w") as fp:
                fp.write(data)
            result = CollectionFile.objects.create(file=os.path.basename(path))
            LOG.debug("Created CollectionFile pk=%d", result.pk)
            return result

        @classmethod
        def create_collection(
            cls,
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
            '"linesCovered":0}',
        ):
            # create collectionfile
            coverage = cls.create_collection_file(coverage)
            # create client
            client, created = Client.objects.get_or_create(name=client)
            if created:
                LOG.debug("Created Client pk=%d", client.pk)
            # create repository
            if repository is None:
                repository = cls.create_repository("git")
            result = Collection.objects.create(
                description=description,
                repository=repository,
                revision=revision,
                branch=branch,
                client=client,
                coverage=coverage,
            )
            LOG.debug("Created Collection pk=%d", result.pk)
            # create tools
            for tool in tools:
                tool, created = Tool.objects.get_or_create(name=tool)
                if created:
                    LOG.debug("Created Tool pk=%d", tool.pk)
                result.tools.add(tool)
            return result

        @staticmethod
        def create_toolfilter(tool_name, user="test"):
            user = User.objects.get(username=user)
            cmuser, _ = cmUser.objects.get_or_create(user=user)
            cmuser.defaultToolsFilter.add(Tool.objects.get(name=tool_name))

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
