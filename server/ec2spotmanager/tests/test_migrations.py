# coding: utf-8
'''
Tests for EC2SpotManager migrations

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import decimal
import pytest


pytestmark = pytest.mark.usefixtures("ec2spotmanager_test")  # pylint: disable=invalid-name


@pytest.mark.migrate_from('0008_remove_aws_creds')  # noqa
@pytest.mark.migrate_to('0009_add_instance_size')
def test_add_instance_size_migrate(migration_hook):
    PoolConfiguration = migration_hook.apps.get_model('ec2spotmanager', 'PoolConfiguration')
    InstancePool = migration_hook.apps.get_model('ec2spotmanager', 'InstancePool')
    Instance = migration_hook.apps.get_model('ec2spotmanager', 'Instance')
    cfg1 = PoolConfiguration.objects.create(
        name='Test config #1',
        size=None,
        ec2_instance_types='["c5.2xlarge"]',
        ec2_max_price=decimal.Decimal('0.10'),
    )
    cfg1_pk = cfg1.pk
    cfg2 = PoolConfiguration.objects.create(
        parent=cfg1,
        name='Test config #2',
        size=None,
    )
    cfg2_pk = cfg2.pk
    cfg3 = PoolConfiguration.objects.create(
        parent=cfg2,
        name='Test config #3',
        size=2,
        ec2_max_price=decimal.Decimal('0.12'),
    )
    cfg3_pk = cfg3.pk
    inst_pk = Instance.objects.create(pool=InstancePool.objects.create(config=cfg3), status_code=0).pk

    # run migration
    migration_hook()

    PoolConfiguration = migration_hook.apps.get_model('ec2spotmanager', 'PoolConfiguration')
    Instance = migration_hook.apps.get_model('ec2spotmanager', 'Instance')
    cfg1 = PoolConfiguration.objects.get(pk=cfg1_pk)
    cfg2 = PoolConfiguration.objects.get(pk=cfg2_pk)
    cfg3 = PoolConfiguration.objects.get(pk=cfg3_pk)
    instance = Instance.objects.get(pk=inst_pk)

    assert cfg1.size is None
    assert cfg1.ec2_instance_types == '["c5.2xlarge"]'
    assert cfg1.ec2_max_price == decimal.Decimal('0.10') / 8

    assert cfg2.size is None
    assert cfg2.ec2_instance_types is None
    assert cfg2.ec2_max_price is None

    assert cfg3.size == 16  # c5.2xlarge has 8 cores
    assert cfg3.ec2_instance_types is None
    assert cfg3.ec2_max_price == decimal.Decimal('0.12') / 8

    assert instance.size == 8


@pytest.mark.migrate_from('0008_remove_aws_creds')  # noqa
@pytest.mark.migrate_to('0009_add_instance_size')
def test_add_instance_size_no_instances(migration_hook):
    PoolConfiguration = migration_hook.apps.get_model('ec2spotmanager', 'PoolConfiguration')
    InstancePool = migration_hook.apps.get_model('ec2spotmanager', 'InstancePool')
    Instance = migration_hook.apps.get_model('ec2spotmanager', 'Instance')
    cfg = PoolConfiguration.objects.create(
        name='Test config #1',
        size=10,
        ec2_max_price=decimal.Decimal('0.10'),
    )
    cfg_pk = cfg.pk
    inst_pk = Instance.objects.create(pool=InstancePool.objects.create(config=cfg), status_code=0).pk

    # run migration
    migration_hook()

    PoolConfiguration = migration_hook.apps.get_model('ec2spotmanager', 'PoolConfiguration')
    Instance = migration_hook.apps.get_model('ec2spotmanager', 'Instance')
    cfg = PoolConfiguration.objects.get(pk=cfg_pk)
    instance = Instance.objects.get(pk=inst_pk)

    assert cfg.size == 10
    assert cfg.ec2_instance_types is None
    assert cfg.ec2_max_price == decimal.Decimal('0.10')

    assert instance.size == 1


@pytest.mark.migrate_from('0008_remove_aws_creds')  # noqa
@pytest.mark.migrate_to('0009_add_instance_size')
def test_add_instance_size_different_sizes(migration_hook):
    PoolConfiguration = migration_hook.apps.get_model('ec2spotmanager', 'PoolConfiguration')
    InstancePool = migration_hook.apps.get_model('ec2spotmanager', 'InstancePool')
    Instance = migration_hook.apps.get_model('ec2spotmanager', 'Instance')
    cfg1 = PoolConfiguration.objects.create(
        name='Test config #1',
        size=3,
        ec2_instance_types='["c5.2xlarge"]',
        ec2_max_price=decimal.Decimal('0.10'),
    )
    cfg1_pk = cfg1.pk
    cfg2 = PoolConfiguration.objects.create(
        parent=cfg1,
        name='Test config #2',
        ec2_instance_types='["c5.xlarge"]',
        size=2,
        ec2_max_price=decimal.Decimal('0.12'),
    )
    cfg2_pk = cfg2.pk
    inst1_pk = Instance.objects.create(pool=InstancePool.objects.create(config=cfg1), status_code=0).pk
    inst2_pk = Instance.objects.create(pool=InstancePool.objects.create(config=cfg2), status_code=0).pk

    # run migration
    migration_hook()

    PoolConfiguration = migration_hook.apps.get_model('ec2spotmanager', 'PoolConfiguration')
    Instance = migration_hook.apps.get_model('ec2spotmanager', 'Instance')
    cfg1 = PoolConfiguration.objects.get(pk=cfg1_pk)
    cfg2 = PoolConfiguration.objects.get(pk=cfg2_pk)
    instance1 = Instance.objects.get(pk=inst1_pk)
    instance2 = Instance.objects.get(pk=inst2_pk)

    # c5.2xlarge has 8 cores
    assert cfg1.size == 24
    assert cfg1.ec2_instance_types == '["c5.2xlarge"]'
    assert cfg1.ec2_max_price == decimal.Decimal('0.10') / 8

    # c5.xlarge has 4 cores, average is 6
    assert cfg2.size == 12
    assert cfg2.ec2_instance_types == '["c5.xlarge"]'
    assert cfg2.ec2_max_price == decimal.Decimal('0.12') / 6

    assert instance1.size == 8
    assert instance2.size == 6
