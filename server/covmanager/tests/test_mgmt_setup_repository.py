# coding: utf-8
'''Tests for CovManager setup_repository management command

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import os
import pytest
from django.core.management import call_command, CommandError
from covmanager.models import Repository


pytestmark = pytest.mark.django_db()  # pylint: disable=invalid-name


def test_bad_args():
    with pytest.raises(CommandError, match=r"Error: .*? arguments"):
        call_command("setup_repository")

    with pytest.raises(CommandError, match=r"Error: .*? arguments"):
        call_command("setup_repository", "")

    with pytest.raises(CommandError, match=r"Error: .*? arguments"):
        call_command("setup_repository", "", "")

    with pytest.raises(CommandError, match=r"Error: invalid repository name"):
        call_command("setup_repository", "", "git", ".")

    with pytest.raises(CommandError, match=r"Error: invalid provider class"):
        call_command("setup_repository", "test", "", ".")

    with pytest.raises(CommandError, match=r"Error: invalid location"):
        call_command("setup_repository", "test", "git", "")

    with pytest.raises(CommandError, match=r"Error: unrecognized arguments: "):
        call_command("setup_repository", "", "", "", "")


def test_repo_exists():
    Repository.objects.create(name="test")
    with pytest.raises(CommandError, match=r"Error: repository with name '.*' already exists!"):
        call_command("setup_repository", "test", "", "")


def test_bad_provider():
    with pytest.raises(CommandError, match=r"Error: 'bad' is not a valid source code provider!"):
        call_command("setup_repository", "test", "bad", ".")


def test_git_create():
    call_command("setup_repository", "test", "git", ".")
    repo = Repository.objects.get(name="test")
    assert repo.classname == "GITSourceCodeProvider"
    assert repo.location == os.path.realpath(".")

    call_command("setup_repository", "test2", "GITSourceCodeProvider", ".")
    repo = Repository.objects.get(name="test2")
    assert repo.classname == "GITSourceCodeProvider"
    assert repo.location == os.path.realpath(".")


def test_hg_create():
    call_command("setup_repository", "test", "hg", ".")
    repo = Repository.objects.get(name="test")
    assert repo.classname == "HGSourceCodeProvider"
    assert repo.location == os.path.realpath(".")

    call_command("setup_repository", "test2", "HGSourceCodeProvider", ".")
    repo = Repository.objects.get(name="test2")
    assert repo.classname == "HGSourceCodeProvider"
    assert repo.location == os.path.realpath(".")
