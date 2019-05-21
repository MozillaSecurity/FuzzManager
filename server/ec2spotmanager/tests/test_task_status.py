# coding: utf-8
'''
Tests for ec2spotmanager task update_status utilities.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import pytest
from ec2spotmanager.models import PoolStatusEntry, ProviderStatusEntry
from ec2spotmanager.tasks import _update_pool_status, _update_provider_status
from . import create_config, create_pool


pytestmark = pytest.mark.usefixtures('ec2spotmanager_test')  # pylint: disable=invalid-name


def test_update_pool_status():
    """test that update_pool_status utility function works"""
    config = create_config(name='config #1', size=4, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], max_price='0.1', ec2_userdata=b'cleverscript')
    pool = create_pool(config=config)
    _update_pool_status(pool, 'price-too-low', 'testing')
    entry = PoolStatusEntry.objects.get()
    assert entry.msg == 'testing'
    assert entry.pool == pool
    assert not entry.isCritical


def test_update_provider_status():
    """test that update_provider_status utility function works"""
    _update_provider_status('EC2Spot', 'price-too-low', 'testing')
    entry = ProviderStatusEntry.objects.get()
    assert entry.msg == 'testing'
    assert entry.provider == 'EC2Spot'
    assert not entry.isCritical
