# coding: utf-8
'''
Tests for ec2spotmanager task graph.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import logging
import pytest
from ec2spotmanager.cron import check_instance_pools
from ec2spotmanager.tasks import terminate_instances
from ec2spotmanager.CloudProvider.CloudProvider import INSTANCE_STATE
from . import create_config, create_instance, create_pool

try:
    from unittest.mock import call
except ImportError:
    from mock import call

LOG = logging.getLogger('fm.ec2spotmanager.tests.task_graph')
pytestmark = pytest.mark.usefixtures('ec2spotmanager_test', 'mock_provider')  # pylint: disable=invalid-name


def test_update_pool_graph(mocker):
    mock_group = mocker.patch('celery.group')
    mock_chain = mocker.patch('celery.chain')
    mock_chord = mocker.patch('celery.chord')
    mock_lock = mocker.patch('ec2spotmanager.cron.RedisLock')
    mock_check_and_resize_pool = mocker.patch('ec2spotmanager.tasks.check_and_resize_pool')
    mock_cycle_and_terminate_disabled = mocker.patch('ec2spotmanager.tasks.cycle_and_terminate_disabled')
    mock_terminate_instances = mocker.patch('ec2spotmanager.tasks.terminate_instances')
    mock_update_instances = mocker.patch('ec2spotmanager.tasks.update_instances')
    mock_update_requests = mocker.patch('ec2spotmanager.tasks.update_requests')
    mock_release_lock = mocker.patch('ec2spotmanager.cron._release_lock')

    config1 = create_config(name='config #1',
                            size=1, cycle_interval=1,
                            ec2_key_name='a',
                            ec2_image_name='a',
                            max_price='0.1',
                            ec2_userdata='a',
                            ec2_allowed_regions=['a', 'b', 'e', 'f'])
    config2 = create_config(name='config #2',
                            size=1, cycle_interval=1,
                            ec2_key_name='a',
                            ec2_image_name='a',
                            max_price='0.1',
                            ec2_userdata='a',
                            ec2_allowed_regions=['a', 'b', 'c', 'd'])
    config3 = create_config(name='config #3',
                            size=1, cycle_interval=1,
                            ec2_key_name='a',
                            ec2_image_name='a',
                            max_price='0.1',
                            ec2_userdata='a',
                            ec2_allowed_regions=['a', 'b'])
    pool1 = create_pool(config=config1, enabled=True)
    pool2 = create_pool(config=config2, enabled=True)
    pool3 = create_pool(config=config3)

    check_instance_pools()

    # there are 2 providers, and 6 provider-regions
    # we should end up with 1 chain per provider-region + 1 final chain
    # each provider chain has 1 group, and the final chain has a group and a chord
    assert mock_group.call_count == 7
    assert mock_chain.call_count == 7
    assert mock_chord.call_count == 1
    assert mock_check_and_resize_pool.si.call_count == 2
    assert mock_cycle_and_terminate_disabled.si.call_count == 6
    assert mock_terminate_instances.s.call_count == 1
    assert mock_update_instances.si.call_count == 6
    assert mock_update_requests.si.call_count == 10
    assert mock_lock.call_count == 1
    assert mock_lock.return_value.acquire.call_count == 1
    assert mock_lock.return_value.release.call_count == 0
    assert mock_release_lock.si.call_count == 2

    cycle_and_terminate_disabled_idx = 0
    update_instances_idx = 0
    update_requests_idx = 0

    group1_regions = set("cdef")
    group3_regions = set("ab")

    for group_call in mock_group.call_args_list:
        LOG.debug("call args length %d", len(group_call[0][0]))
        if len(group_call[0][0]) == 1:
            assert group_call == call([mock_update_requests.si()])
            region = mock_update_requests.si.call_args_list[update_requests_idx][0][1]
            LOG.debug("region %s", region)
            assert region in group1_regions
            group1_regions.remove(region)
            provider = 'prov1' if region in set('abcd') else 'prov2'
            pool = pool1.pk if region in 'ef' else pool2.pk
            assert mock_update_requests.si.call_args_list[update_requests_idx] == call(provider, region, pool)
            assert mock_update_instances.si.call_args_list[update_instances_idx] == call(provider, region)
            assert mock_cycle_and_terminate_disabled.si.call_args_list[cycle_and_terminate_disabled_idx] == \
                call(provider, region)
            update_requests_idx += 1
            update_instances_idx += 1
            cycle_and_terminate_disabled_idx += 1
        elif len(group_call[0][0]) == 3:
            assert group_call == call([mock_update_requests.si(), mock_update_requests.si(), mock_update_requests.si()])
            region = mock_update_requests.si.call_args_list[update_requests_idx][0][1]
            LOG.debug("region %s", region)
            assert region in group3_regions
            group3_regions.remove(region)
            assert mock_update_requests.si.call_args_list[update_requests_idx] == call('prov1', region, pool1.pk)
            assert mock_update_requests.si.call_args_list[update_requests_idx + 1] == call('prov1', region, pool2.pk)
            assert mock_update_requests.si.call_args_list[update_requests_idx + 2] == call('prov1', region, pool3.pk)
            assert mock_update_instances.si.call_args_list[update_instances_idx] == call('prov1', region)
            assert mock_cycle_and_terminate_disabled.si.call_args_list[cycle_and_terminate_disabled_idx] == \
                call('prov1', region)
            update_requests_idx += 3
            update_instances_idx += 1
            cycle_and_terminate_disabled_idx += 1
        else:
            assert group_call == call([mock_chain(), mock_chain(), mock_chain(), mock_chain(), mock_chain(),
                                       mock_chain()])

    assert mock_chord.call_args == call([mock_check_and_resize_pool.si(), mock_check_and_resize_pool.si()],
                                        mock_terminate_instances.s())
    assert mock_check_and_resize_pool.si.call_args_list[0] == call(pool1.pk)
    assert mock_check_and_resize_pool.si.call_args_list[1] == call(pool2.pk)

    assert mock_terminate_instances.s.call_args_list[0] == call()

    assert cycle_and_terminate_disabled_idx == 6
    assert update_instances_idx == 6
    assert update_requests_idx == 10

    assert not group1_regions
    assert not group3_regions

    for i in range(6):
        assert mock_chain.call_args_list[i] == call(mock_group(), mock_update_instances.si(),
                                                    mock_cycle_and_terminate_disabled.si())
    assert mock_chain.call_args_list[6] == call(mock_group(), mock_chord(), mock_release_lock.si())
    assert mock_chain.return_value.on_error.call_count == 1
    assert mock_chain.return_value.on_error.return_value.call_count == 1
    assert mock_chain.return_value.on_error.return_value.call_args == call()


def test_update_pool_graph_unsupported_running(mocker):
    """check that unsupported but running instances are still updated
    eg. if a config is edited to exclude a provider, but there are already instances. we should still update them.
    """
    mock_group = mocker.patch('celery.group')
    mock_chain = mocker.patch('celery.chain')
    mock_chord = mocker.patch('celery.chord')
    mock_lock = mocker.patch('ec2spotmanager.cron.RedisLock')
    mock_check_and_resize_pool = mocker.patch('ec2spotmanager.tasks.check_and_resize_pool')
    mock_cycle_and_terminate_disabled = mocker.patch('ec2spotmanager.tasks.cycle_and_terminate_disabled')
    mock_terminate_instances = mocker.patch('ec2spotmanager.tasks.terminate_instances')
    mock_update_instances = mocker.patch('ec2spotmanager.tasks.update_instances')
    mock_update_requests = mocker.patch('ec2spotmanager.tasks.update_requests')
    mock_release_lock = mocker.patch('ec2spotmanager.cron._release_lock')

    config = create_config(name='config #1',
                           size=1, cycle_interval=1,
                           ec2_key_name='a',
                           ec2_image_name='a',
                           max_price='0.1',
                           ec2_userdata='a',
                           ec2_allowed_regions=['a'])
    pool = create_pool(config=config, enabled=False)
    create_instance(None, pool=pool, status_code=INSTANCE_STATE['requested'],
                    ec2_instance_id='r-123', ec2_region='f', provider='prov2')

    check_instance_pools()

    # there are 2 providers, and 3 provider-regions
    # we should end up with 1 chain per provider-region + 1 final chain
    # each provider chain has 1 group, and the final chain has 1 group and 1 chord
    assert mock_group.call_count == 3
    assert mock_chain.call_count == 3
    assert mock_chord.call_count == 1
    assert mock_check_and_resize_pool.si.call_count == 0
    assert mock_cycle_and_terminate_disabled.si.call_count == 2
    assert mock_terminate_instances.s.call_count == 1
    assert mock_update_instances.si.call_count == 2
    assert mock_update_requests.si.call_count == 2
    assert mock_lock.call_count == 1
    assert mock_lock.return_value.acquire.call_count == 1
    assert mock_lock.return_value.release.call_count == 0
    assert mock_release_lock.si.call_count == 2

    cycle_and_terminate_disabled_idx = 0
    update_instances_idx = 0
    update_requests_idx = 0

    group_regions = set("af")

    for group_call in mock_group.call_args_list:
        LOG.debug("call args length %d", len(group_call[0][0]))
        if len(group_call[0][0]) == 1:
            assert group_call == call([mock_update_requests.si()])
            region = mock_update_requests.si.call_args_list[update_requests_idx][0][1]
            LOG.debug("region %s", region)
            assert region in group_regions
            group_regions.remove(region)
            provider = 'prov1' if region in set('abcd') else 'prov2'
            assert mock_update_requests.si.call_args_list[update_requests_idx] == call(provider, region, pool.pk)
            assert mock_update_instances.si.call_args_list[update_instances_idx] == call(provider, region)
            assert mock_cycle_and_terminate_disabled.si.call_args_list[cycle_and_terminate_disabled_idx] == \
                call(provider, region)
            update_requests_idx += 1
            update_instances_idx += 1
            cycle_and_terminate_disabled_idx += 1
            pass
        elif group_call[0][0]:
            assert group_call == call([mock_chain(), mock_chain()])

    assert mock_chord.call_args == call([], mock_terminate_instances.s())

    assert mock_terminate_instances.s.call_args_list[0] == call()

    assert cycle_and_terminate_disabled_idx == 2
    assert update_instances_idx == 2
    assert update_requests_idx == 2

    assert not group_regions

    for i in range(2):
        assert mock_chain.call_args_list[i] == call(mock_group(), mock_update_instances.si(),
                                                    mock_cycle_and_terminate_disabled.si())
    assert mock_chain.call_args_list[2] == call(mock_group(), mock_chord(), mock_release_lock.si())
    assert mock_chain.return_value.on_error.call_count == 1
    assert mock_chain.return_value.on_error.return_value.call_count == 1
    assert mock_chain.return_value.on_error.return_value.call_args == call()


def test_terminate_instances(mocker):
    """test that terminate instances triggers the appropriate subtasks"""
    mock_group = mocker.patch('celery.group')
    mock_term_instance = mocker.patch('ec2spotmanager.tasks._terminate_instance_ids')
    mock_term_request = mocker.patch('ec2spotmanager.tasks._terminate_instance_request_ids')

    cfg = create_config(name='test config')
    pool = create_pool(config=cfg)

    inst1 = create_instance(None, pool=pool, status_code=INSTANCE_STATE['requested'],
                            ec2_instance_id='r-123', ec2_region='redmond', ec2_zone='mshq')
    inst2 = create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                            ec2_instance_id='i-456', ec2_region='redmond', ec2_zone='mshq')
    inst3 = create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                            ec2_instance_id='i-789', ec2_region='bellevue', ec2_zone='mshq')
    terminate_instances([[inst1.pk], [inst2.pk, inst3.pk]])

    assert mock_group.call_count == 1
    mock_group.assert_called_once_with([call(), call(), call()])
    mock_group.return_value.delay.assert_called_once_with()

    assert mock_term_instance.si.call_count == 2
    assert mock_term_request.si.call_count == 1

    mock_term_instance.si.assert_any_call('EC2Spot', 'redmond', ['i-456'])
    mock_term_instance.si.assert_any_call('EC2Spot', 'bellevue', ['i-789'])
    mock_term_request.si.assert_any_call('EC2Spot', 'redmond', ['r-123'])
