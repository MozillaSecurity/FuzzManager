# coding: utf-8
'''
Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import functools
import sys
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Permission
import pytest
from crashmanager.models import User as cmUser
from ec2spotmanager.CloudProvider.CloudProvider import CloudProvider
from . import UncatchableException

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock


def _create_user(username, email="test@mozilla.com", password="test", has_permission=True):
    user = User.objects.create_user(username, email, password)
    user.user_permissions.clear()
    if has_permission:
        content_type = ContentType.objects.get_for_model(cmUser)
        perm = Permission.objects.get(content_type=content_type, codename='view_ec2spotmanager')
        user.user_permissions.add(perm)
    (user, _) = cmUser.get_or_create_restricted(user)
    user.save()
    return user


@pytest.fixture
def ec2spotmanager_test(db):  # pylint: disable=invalid-name,unused-argument
    """Common testcase class for all ec2spotmanager unittests"""
    # Create one unrestricted and one restricted test user
    _create_user("test")
    _create_user("test-noperm", has_permission=False)


@pytest.fixture
def mock_provider(mocker):
    prv_t = Mock(spec=CloudProvider)

    def allowed_regions(cls, cfg):
        result = []
        if cls.provider == 'prov1':
            result.extend(set(cfg.ec2_allowed_regions) & set("abcd"))
        if cls.provider == 'prov2':
            result.extend(set(cfg.ec2_allowed_regions) & set("ef"))
        result.sort()
        return result

    def get_instance(cls, provider):
        cls.provider = provider
        return cls
    prv_t.check_instances_state.return_value = {}
    prv_t.get_allowed_regions = functools.partial(allowed_regions, prv_t)
    prv_t.get_cores_per_instance.return_value = {}
    prv_t.get_instance = functools.partial(get_instance, prv_t)
    prv_t.get_instance_types = lambda cfg: cfg.ec2_instance_types

    mocker.patch('ec2spotmanager.cron.PROVIDERS', new=['prov1', 'prov2'])
    mocker.patch('ec2spotmanager.cron.CloudProvider', new=prv_t)
    mocker.patch('ec2spotmanager.tasks.PROVIDERS', new=['prov1', 'prov2'])
    return mocker.patch('ec2spotmanager.tasks.CloudProvider', new=prv_t)


@pytest.fixture
def raise_on_status(mocker):

    def _mock_pool_status(_pool, type_, message):
        if sys.exc_info() != (None, None, None):
            raise  # pylint: disable=misplaced-bare-raise
        raise UncatchableException("%s: %s" % (type_, message))

    mocker.patch('ec2spotmanager.tasks._update_pool_status', new=Mock(side_effect=_mock_pool_status))
    mocker.patch('ec2spotmanager.tasks._update_provider_status', new=Mock(side_effect=_mock_pool_status))
