"""Common test fixtures

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
from typing import cast

import py as py_package
import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import Storage
from pytest_django.fixtures import SettingsWrapper
from typing_extensions import TypedDict

from covmanager.models import Collection, CollectionFile, Repository
from crashmanager.models import Client, Tool
from crashmanager.models import User as cmUser

LOG = logging.getLogger("fm.covmanager.tests")


def _check_git() -> bool:
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


def _check_hg() -> bool:
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


@pytest.fixture
def covmanager_test(db: None) -> None:  # pylint: disable=invalid-name,unused-argument
    """Common setup/teardown tasks for all server unittests"""
    user = User.objects.create_user("test", "test@mozilla.com", "test")
    user.user_permissions.clear()
    content_type = ContentType.objects.get_for_model(cmUser)
    perm = Permission.objects.get(content_type=content_type, codename="view_covmanager")
    user.user_permissions.add(perm)
    user_np = User.objects.create_user("test-noperm", "test@mozilla.com", "test")
    user_np.user_permissions.clear()


class covType(TypedDict):
    """Type information for cov"""

    children: dict[str, str]
    coveragePercent: float
    linesCovered: int
    linesMissed: int
    linesTotal: int
    name: str | None


class _result:  # pylint: disable=invalid-name
    have_git: bool
    have_hg: bool

    @classmethod
    def create_repository(cls, repotype: str, name: str = "testrepo") -> Repository:
        ...

    @staticmethod
    def create_collection_file(data: str) -> CollectionFile:
        ...

    @classmethod
    def create_collection(
        cls,
        created: bool | None = None,
        description: str = "",
        repository: Repository | None = None,
        revision: str = "",
        branch: str = "",
        tools: tuple[str] = ("testtool",),
        client: str = "testclient",
        coverage: str = '{"linesTotal":0,'
        '"name":null,'
        '"coveragePercent":0.0,'
        '"children":{},'
        '"linesMissed":0,'
        '"linesCovered":0}',
    ) -> Collection:
        ...

    @staticmethod
    def git(repo: Repository, *args: str) -> str:
        ...

    @staticmethod
    def hg(repo: Repository, *args: str) -> str:
        ...


@pytest.fixture
def cm(
    request: pytest.FixtureRequest,
    settings: SettingsWrapper,
    tmpdir: py_package.path.local,
):
    class _result:
        have_git = HAVE_GIT
        have_hg = HAVE_HG

        @classmethod
        def create_repository(cls, repotype: str, name: str = "testrepo") -> Repository:
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
            result = cast(
                Repository,
                Repository.objects.create(
                    classname=classname, name=name, location=location
                ),
            )
            LOG.debug("Created Repository pk=%d", result.pk)
            if repotype == "git":
                cls.git(result, "init")
            elif repotype == "hg":
                cls.hg(result, "init")
            return result

        @staticmethod
        def create_collection_file(data: str) -> CollectionFile:

            # Use a specific temporary directory to upload covmanager files.  This is
            # required as Django now needs a path relative to that folder in FileField
            location = str(tmpdir)
            assert isinstance(CollectionFile.file.field.storage, Storage)
            CollectionFile.file.field.storage.location = location

            tmp_fd, path = tempfile.mkstemp(suffix=".data", dir=location)
            os.close(tmp_fd)
            with open(path, "w") as fp:
                fp.write(data)
            result = cast(
                CollectionFile,
                CollectionFile.objects.create(file=os.path.basename(path)),
            )
            LOG.debug("Created CollectionFile pk=%d", result.pk)
            return result

        @classmethod
        def create_collection(
            cls,
            created: bool | None = None,
            description: str = "",
            repository: Repository | None = None,
            revision: str = "",
            branch: str = "",
            tools: tuple[str] = ("testtool",),
            client: str = "testclient",
            coverage: str = '{"linesTotal":0,'
            '"name":null,'
            '"coveragePercent":0.0,'
            '"children":{},'
            '"linesMissed":0,'
            '"linesCovered":0}',
        ) -> Collection:
            # create collectionfile
            coverage_ = cls.create_collection_file(coverage)
            # create client
            client_, created = Client.objects.get_or_create(name=client)
            if created:
                LOG.debug("Created Client pk=%d", client_.pk)
            # create repository
            if repository is None:
                repository = cls.create_repository("git")
            result = cast(
                Collection,
                Collection.objects.create(
                    description=description,
                    repository=repository,
                    revision=revision,
                    branch=branch,
                    client=client_,
                    coverage=coverage_,
                ),
            )
            LOG.debug("Created Collection pk=%d", result.pk)
            # create tools
            for single_tool in tools:
                tool, created = Tool.objects.get_or_create(name=single_tool)
                if created:
                    LOG.debug("Created Tool pk=%d", tool.pk)
                result.tools.add(tool)
            return result

        @staticmethod
        def git(repo: Repository, *args: str) -> str:
            path = os.getcwd()
            try:
                os.chdir(repo.location)
                return subprocess.check_output(["git"] + list(args)).decode("utf-8")
            finally:
                os.chdir(path)

        @staticmethod
        def hg(repo: Repository, *args: str) -> str:
            path = os.getcwd()
            try:
                os.chdir(repo.location)
                return subprocess.check_output(["hg"] + list(args)).decode("utf-8")
            finally:
                os.chdir(path)

    return _result()
