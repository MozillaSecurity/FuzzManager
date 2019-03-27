# coding: utf-8
'''
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
import os
import pytest
import shutil
from covmanager.SourceCodeProvider.GITSourceCodeProvider import GITSourceCodeProvider
from covmanager.SourceCodeProvider.HGSourceCodeProvider import HGSourceCodeProvider
from covmanager.SourceCodeProvider.SourceCodeProvider import Utils


@pytest.fixture
def git_repo(tmp_path):
    shutil.copytree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test-git"),
                    str(tmp_path / "test-git"))
    (tmp_path / "test-git" / "git").rename(tmp_path / "test-git" / ".git")
    yield str(tmp_path / "test-git")


@pytest.fixture
def hg_repo(tmp_path):
    shutil.copytree(os.path.join(os.path.dirname(os.path.abspath(__file__)), "test-hg"),
                    str(tmp_path / "test-hg"))
    (tmp_path / "test-hg" / "hg").rename(tmp_path / "test-hg" / ".hg")
    yield str(tmp_path / "test-hg")


def test_GITSourceCodeProvider(git_repo):
    provider = GITSourceCodeProvider(git_repo)

    tests = {
        "a.txt": {
            "dcbe8ca3dafb34bc90984fb1d74305baf2c58f17": "Hello world\n",
            "474f46342c82059a819ce7cd3d5e3e0695b9b737": "I'm sorry Dave,\nI'm afraid I can't do that.\n"
        },
        "abc/def.txt": {
            "deede1283a224184f6654027e23b654a018e81b0": ("Hi there!\n\nI'm a multi-line file,\n\n"
                                                         "nice to meet you.\n"),
            "474f46342c82059a819ce7cd3d5e3e0695b9b737": "Hi there!\n\nI'm a multi-line file,\n\nnice to meet you.\n"
        }
    }

    for filename in tests:
        for revision in tests[filename]:
            assert provider.testRevision(revision), "Revision %s is unknown" % revision
            assert provider.getSource(filename, revision) == tests[filename][revision]

    parents = provider.getParents("deede1283a224184f6654027e23b654a018e81b0")
    assert len(parents) == 1
    assert parents[0] == "dcbe8ca3dafb34bc90984fb1d74305baf2c58f17"

    parents = provider.getParents("dcbe8ca3dafb34bc90984fb1d74305baf2c58f17")
    assert len(parents) == 0


def test_HGSourceCodeProvider(hg_repo):
    provider = HGSourceCodeProvider(hg_repo)

    tests = {
        "a.txt": {
            "c3abaa766d52f438219920d37461b341321d4fef": "Hello world\n",
            "c179ace9e260adbabd17426750b5a62403691624": "I'm sorry Dave,\nI'm afraid I can't do that.\n"
        },
        "abc/def.txt": {
            "05ceb4ce5ed96a107fb40e3b39df7da18f0780c3": ("Hi there!\n\nI'm a multi-line file,\n\n"
                                                         "nice to meet you.\n"),
            "c179ace9e260adbabd17426750b5a62403691624": "Hi there!\n\nI'm a multi-line file,\n\nnice to meet you.\n"
        }
    }

    for filename in tests:
        for revision in tests[filename]:
            assert provider.testRevision(revision), "Revision %s is unknown" % revision
            assert provider.getSource(filename, revision) == tests[filename][revision]

    parents = provider.getParents("7a6e60cac455")
    assert len(parents) == 1
    assert parents[0] == "05ceb4ce5ed96a107fb40e3b39df7da18f0780c3"

    parents = provider.getParents("c3abaa766d52")
    assert len(parents) == 0


@pytest.mark.skipif(not os.path.isdir("/home/decoder/Mozilla/repos/mozilla-central-fm"), reason="not decoder")
def test_HGDiff():
    provider = HGSourceCodeProvider("/home/decoder/Mozilla/repos/mozilla-central-fm")
    diff = provider.getUnifiedDiff("4f8e0cb21016")

    print(Utils.getDiffLocations(diff))


def test_HGRevisionEquivalence():
    provider = HGSourceCodeProvider("")

    # Simple equality for short and long revision formats
    assert provider.checkRevisionsEquivalent("c179ace9e260", "c179ace9e260")
    assert provider.checkRevisionsEquivalent(
        "c179ace9e260adbabd17426750b5a62403691624",
        "c179ace9e260adbabd17426750b5a62403691624"
    )

    # Equivalence of long and short format
    assert provider.checkRevisionsEquivalent("c179ace9e260", "c179ace9e260adbabd17426750b5a62403691624")
    assert provider.checkRevisionsEquivalent("c179ace9e260adbabd17426750b5a62403691624", "c179ace9e260")

    # Negative tests
    assert not provider.checkRevisionsEquivalent("", "c179ace9e260")
    assert not provider.checkRevisionsEquivalent("c179ace9e260", "")
    assert not provider.checkRevisionsEquivalent("7a6e60cac455", "c179ace9e260")
    assert not provider.checkRevisionsEquivalent("7a6e60cac455", "c179ace9e260adbabd17426750b5a62403691624")
    assert not provider.checkRevisionsEquivalent("c179ace9e260adbabd17426750b5a62403691624", "7a6e60cac455")
    assert not provider.checkRevisionsEquivalent(
        "c3abaa766d52f438219920d37461b341321d4fef",
        "c179ace9e260adbabd17426750b5a62403691624"
    )
