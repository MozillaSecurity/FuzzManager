# coding: utf-8
'''
Tests for ec2spotmanager tasks.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import datetime
import logging
import sys
import boto.ec2
import pytest
from django.utils import timezone
from . import create_config, create_instance, create_pool
from ec2spotmanager.tasks import check_instance_pool, _update_pool_status
from ec2spotmanager.models import Instance, PoolStatusEntry
from ec2spotmanager.CloudProvider.CloudProvider import INSTANCE_STATE

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


LOG = logging.getLogger('fm.ec2spotmanager.tests.tasks')
pytestmark = pytest.mark.usefixtures('ec2spotmanager_test')  # pylint: disable=invalid-name


class UncatchableException(BaseException):
    """Exception that does not inherit from Exception, so will not be caught by normal exception handling."""
    pass


def _mock_pool_status(_pool, type_, message):
    if sys.exc_info() != (None, None, None):
        raise  # pylint: disable=misplaced-bare-raise
    raise UncatchableException("%s: %s" % (type_, message))


@patch('fasteners.InterProcessLock', new=Mock())
@patch('ec2spotmanager.tasks._update_pool_status', new=Mock(side_effect=_mock_pool_status))
def test_nothing_to_do():
    """nothing is done if no pools are enabled"""
    config = create_config(name='config #1', size=1, cycle_interval=1, ec2_key_name='a', ec2_image_name='a',
                           ec2_max_price='0.1', userdata='a', ec2_allowed_regions=['a'])
    pool = create_pool(config=config)
    check_instance_pool(pool.id)
    assert not Instance.objects.exists()


@patch('fasteners.InterProcessLock', new=Mock())
@patch('ec2spotmanager.tasks._update_pool_status', new=Mock(side_effect=_mock_pool_status))
def test_bad_config():
    """invalid configs create a pool status entry"""
    config = create_config(name='config #1')
    pool = create_pool(config=config)
    with pytest.raises(UncatchableException, match=r'Configuration error \(missing: '):
        check_instance_pool(pool.id)
    assert not Instance.objects.exists()

    config2 = create_config(name='config #2', parent=config)
    config.parent = config2
    config.save()
    with pytest.raises(UncatchableException, match=r'Configuration error \(cyclic\)'):
        check_instance_pool(pool.id)
    assert not Instance.objects.exists()


@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.CORES_PER_INSTANCE', new={'80286': 1})
@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
@patch('redis.StrictRedis')
@patch('fasteners.InterProcessLock', new=Mock())
@patch('ec2spotmanager.tasks._update_pool_status', new=Mock(side_effect=_mock_pool_status))
def test_create_instance(mock_redis, mock_ec2mgr):
    """spot instance requests are created when required"""
    # set-up redis mock to return price data and image name
    def _mock_redis_get(key):
        if ":blacklist:mshq:" in key:
            return True
        if ":blacklist:" in key:
            return None
        if ":price:" in key:
            return '{"redmond": {"mshq": [0.005]}, "toronto": {"markham": [0.01]}}'
        if ":image:" in key:
            return 'warp'
        raise UncatchableException("unhandle key in mock_get(): %s" % (key,))
    mock_redis.return_value.get = Mock(side_effect=_mock_redis_get)

    # ensure EC2Manager returns a request ID
    mock_ec2mgr.return_value.create_spot_requests.return_value = ('req123',)

    # create database state
    config = create_config(name='config #1', size=1, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond', 'toronto'], ec2_max_price='0.1', userdata=b'cleverscript')
    pool = create_pool(config=config, enabled=True)

    # call function under test
    check_instance_pool(pool.id)

    # check that laniakea calls were made
    cluster = mock_ec2mgr.return_value
    assert {call[0] for call in cluster.method_calls} == {'connect', 'create_spot_requests'}

    # check that pending instances were created
    instance = Instance.objects.get()
    assert instance.region == 'toronto'
    assert instance.zone == 'markham'
    assert instance.status_code == INSTANCE_STATE["requested"]
    assert instance.pool.id == pool.id
    assert instance.size == 1
    assert instance.instance_id == 'req123'


@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
@patch('fasteners.InterProcessLock', new=Mock())
@patch('ec2spotmanager.tasks._update_pool_status', new=Mock(side_effect=_mock_pool_status))
def test_fulfilled_spot_instance(mock_ec2mgr):
    """spot instance requests are turned into instances when fulfilled"""
    # ensure EC2Manager returns a request ID
    class _MockInstance(boto.ec2.instance.Instance):
        def __init__(self, *args, **kwds):
            super(_MockInstance, self).__init__(*args, **kwds)
            self._test_tags = {}

        @property
        def state_code(self):
            return INSTANCE_STATE['running']

        def add_tags(self, tags, dry_run=False):
            self._test_tags.update(tags)
    boto_instance = _MockInstance()
    boto_instance.id = 'i-123'
    boto_instance.public_dns_name = 'fm-test.fuzzing.allizom.com'
    mock_ec2mgr.return_value.check_spot_requests.return_value = (boto_instance,)

    # create database state
    config = create_config(name='config #1', size=1, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], ec2_max_price='0.1', userdata=b'cleverscript')
    pool = create_pool(config=config, enabled=True)
    orig = create_instance(None, pool=pool, status_code=INSTANCE_STATE['requested'],
                           ec2_instance_id='req123', ec2_region="redmond", ec2_zone="mshq")

    # call function under test
    check_instance_pool(pool.id)

    # check that laniakea calls were made
    cluster = mock_ec2mgr.return_value
    assert {call[0] for call in cluster.method_calls} == {'connect', 'check_spot_requests', 'find'}

    # check that instance was updated
    instance = Instance.objects.get()
    assert instance.id == orig.id
    assert instance.hostname == 'fm-test.fuzzing.allizom.com'
    assert instance.status_code == INSTANCE_STATE["running"]
    assert instance.instance_id == 'i-123'
    assert boto_instance._test_tags == {'SpotManager-Updatable': '1'}  # pylint: disable=protected-access


@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.CORES_PER_INSTANCE', new={'80286': 1})
@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
@patch('redis.StrictRedis')
@patch('fasteners.InterProcessLock', new=Mock())
@patch('ec2spotmanager.tasks._update_pool_status', new=Mock(side_effect=_mock_pool_status))
def test_instance_shutting_down(mock_redis, mock_ec2mgr):
    """instances are replaced when shut down or terminated"""
    # ensure EC2Manager returns a request ID
    class _MockInstance(boto.ec2.instance.Instance):
        @property
        def state_code(self):
            return INSTANCE_STATE['shutting-down']

        def add_tags(self, _tags, _dry_run=False):
            pass

    class _MockInstance2(_MockInstance):
        @property
        def state_code(self):
            return INSTANCE_STATE['terminated']
    boto_instance1 = _MockInstance()
    boto_instance1.id = 'i-123'
    boto_instance1.public_dns_name = 'fm-test1.fuzzing.allizom.com'
    boto_instance2 = _MockInstance2()
    boto_instance2.id = 'i-456'
    boto_instance2.public_dns_name = 'fm-test2.fuzzing.allizom.com'
    mock_ec2mgr.return_value.find.return_value = (boto_instance1, boto_instance2)

    # set-up redis mock to return price data and image name
    def _mock_redis_get(key):
        if ":blacklist:" in key:
            return None
        if ":price:" in key:
            return '{"redmond": {"mshq": [0.005]}}'
        if ":image:" in key:
            return 'warp'
        raise UncatchableException("unhandle key in mock_get(): %s" % (key,))
    mock_redis.return_value.get = Mock(side_effect=_mock_redis_get)

    # ensure EC2Manager returns a request ID
    mock_ec2mgr.return_value.create_spot_requests.return_value = ('req123', 'req456')

    # create database state
    config = create_config(name='config #1', size=2, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], ec2_max_price='0.1', userdata=b'cleverscript')
    pool = create_pool(config=config, enabled=True)
    orig1 = create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                            ec2_instance_id='i-123', ec2_region="redmond", ec2_zone="mshq")
    orig2 = create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                            ec2_instance_id='i-456', ec2_region="redmond", ec2_zone="mshq")

    # call function under test
    check_instance_pool(pool.id)

    # check that laniakea calls were made
    cluster = mock_ec2mgr.return_value
    assert {call[0] for call in cluster.method_calls} == {'connect', 'create_spot_requests', 'find'}

    # check that instances were replaced
    remaining = {'req123', 'req456'}
    for new in Instance.objects.all():
        assert new.id not in {orig1.id, orig2.id}
        assert new.pool.id == pool.id
        assert new.size == 1
        assert new.status_code == INSTANCE_STATE["requested"]
        remaining.remove(new.instance_id)


@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
@patch('fasteners.InterProcessLock', new=Mock())
@patch('ec2spotmanager.tasks._update_pool_status', new=Mock(side_effect=_mock_pool_status))
def test_instance_not_updatable(mock_ec2mgr):
    """instances are not touched while they are not tagged Updatable"""
    # ensure EC2Manager returns a request ID
    class _MockInstance(boto.ec2.instance.Instance):
        @property
        def state_code(self):
            return INSTANCE_STATE['stopping']

    boto_instance = _MockInstance()
    boto_instance.id = 'i-123'
    boto_instance.public_dns_name = 'fm-test.fuzzing.allizom.com'
    mock_ec2mgr.return_value.find.return_value = (boto_instance,)

    # create database state
    config = create_config(name='config #1', size=1, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], ec2_max_price='0.1', userdata=b'cleverscript')
    pool = create_pool(config=config, enabled=True, last_cycled=timezone.now())
    orig = create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                           ec2_instance_id='i-123', ec2_region="redmond", ec2_zone="mshq")

    # call function under test
    check_instance_pool(pool.id)

    # check that laniakea calls were made
    cluster = mock_ec2mgr.return_value
    assert {call[0] for call in cluster.method_calls} == {'connect', 'find'}

    # check that instances were not updated
    count = 0
    for instance in Instance.objects.all():
        assert instance.status_code == INSTANCE_STATE["running"]
        assert instance.id == orig.id
        count += 1
    assert count == 1


@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.CORES_PER_INSTANCE', new={'80286': 1})
@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
@patch('redis.StrictRedis')
@patch('fasteners.InterProcessLock', new=Mock())
@patch('ec2spotmanager.tasks._update_pool_status', new=Mock(side_effect=_mock_pool_status))
def test_instance_price_high(mock_redis, mock_ec2mgr):
    """check that instances are not created if the price is too high"""
    # set-up redis mock to return price data and image name
    def _mock_redis_get(key):
        if ":blacklist:" in key:
            return None
        if ":price:" in key:
            return '{"redmond": {"mshq": [0.05]}}'
        if ":image:" in key:
            return 'warp'
        raise UncatchableException("unhandle key in mock_get(): %s" % (key,))
    mock_redis.return_value.get = Mock(side_effect=_mock_redis_get)

    # create database state
    config = create_config(name='config #1', size=1, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], ec2_max_price='0.01', userdata=b'cleverscript')
    pool = create_pool(config=config, enabled=True)

    # call function under test
    with pytest.raises(UncatchableException, match="No allowed regions was cheap enough to spawn instances"):
        check_instance_pool(pool.id)

    # check that laniakea calls were made
    cluster = mock_ec2mgr.return_value
    assert not cluster.method_calls

    # check that no instances were created
    assert not Instance.objects.exists()


@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.CORES_PER_INSTANCE', new={'80286': 1})
@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
@patch('redis.StrictRedis')
@patch('fasteners.InterProcessLock', new=Mock())
@patch('ec2spotmanager.tasks._update_pool_status', new=Mock(side_effect=_mock_pool_status))
def test_spot_instance_blacklist(mock_redis, mock_ec2mgr):
    """check that spot requests being cancelled will result in temporary blacklisting"""
    # ensure EC2Manager returns a request ID
    class _MockReq(boto.ec2.spotinstancerequest.SpotInstanceRequest):
        def __init__(self, *args, **kwds):
            super(_MockReq, self).__init__(*args, **kwds)
            self.state = 'cancelled'
    req = _MockReq()
    req.launch_specification = Mock()
    req.launch_specification.instance_type = '80286'
    mock_ec2mgr.return_value.check_spot_requests.return_value = (req,)

    # set-up redis mock to return price data and image name
    def _mock_redis_get(key):
        if ":blacklist:" in key:
            return True
        if ":price:" in key:
            return '{"redmond": {"mshq": [0.001]}}'
        if ":image:" in key:
            return 'warp'
        raise UncatchableException("unhandle key in mock_get(): %s" % (key,))

    def _mock_redis_set(key, value, ex=None):
        assert ":blacklist:mshq:" in key
    mock_redis.return_value.get = Mock(side_effect=_mock_redis_get)
    mock_redis.return_value.set = Mock(side_effect=_mock_redis_set)

    # create database state
    config = create_config(name='config #1', size=1, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], ec2_max_price='0.1', userdata=b'cleverscript')
    pool = create_pool(config=config, enabled=True)
    create_instance(None, pool=pool, status_code=INSTANCE_STATE['requested'],
                    ec2_instance_id='req123', ec2_region="redmond", ec2_zone="mshq")

    # call function under test
    # XXX: this message is inaccurate .. there were no allowed regions at all
    with pytest.raises(UncatchableException, match="No allowed regions was cheap enough to spawn instances"):
        check_instance_pool(pool.id)

    # check that laniakea calls were made
    cluster = mock_ec2mgr.return_value
    assert {call[0] for call in cluster.method_calls} == {'connect', 'check_spot_requests', 'find'}

    # check that instance was updated
    assert not Instance.objects.exists()

    # check that blacklist was set in redis
    assert len(mock_redis.return_value.set.mock_calls) == 1


@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.CORES_PER_INSTANCE', new={'80286': 1})
@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
@patch('redis.StrictRedis')
@patch('fasteners.InterProcessLock', new=Mock())
@patch('ec2spotmanager.tasks._update_pool_status', new=Mock(side_effect=_mock_pool_status))
def test_pool_disabled(mock_redis, mock_ec2mgr):
    """check that pool disabled results in running and pending instances being terminated"""
    # ensure EC2Manager returns a request ID
    class _MockInstance(boto.ec2.instance.Instance):
        @property
        def state_code(self):
            return INSTANCE_STATE['running']
    boto_instance = _MockInstance()
    boto_instance.id = 'i-123'
    boto_instance.public_dns_name = 'fm-test1.fuzzing.allizom.com'
    mock_ec2mgr.return_value.find.return_value = (boto_instance,)
    mock_ec2mgr.return_value.check_spot_requests.return_value = (None,)

    # set-up redis mock to return price data and image name
    def _mock_redis_get(key):
        if ":blacklist:" in key:
            return None
        if ":price:" in key:
            return '{"redmond": {"mshq": [0.005]}}'
        if ":image:" in key:
            return 'warp'
        raise UncatchableException("unhandle key in mock_get(): %s" % (key,))
    mock_redis.return_value.get = Mock(side_effect=_mock_redis_get)

    # ensure EC2Manager returns a request ID
    mock_ec2mgr.return_value.create_spot_requests.return_value = ('req123', 'req456')

    # create database state
    config = create_config(name='config #1', size=2, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], ec2_max_price='0.1', userdata=b'cleverscript')
    pool = create_pool(config=config)
    create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                    ec2_instance_id='i-123', ec2_region="redmond", ec2_zone="mshq")
    create_instance(None, pool=pool, status_code=INSTANCE_STATE['requested'],
                    ec2_instance_id='r-456', ec2_region="redmond", ec2_zone="mshq")

    # call function under test
    check_instance_pool(pool.id)

    # check that laniakea calls were made
    cluster = mock_ec2mgr.return_value
    assert {call[0] for call in cluster.method_calls} == {'connect', 'find', 'terminate', 'check_spot_requests',
                                                          'cancel_spot_requests'}
    cluster.terminate.assert_called_once_with((boto_instance,))
    cluster.cancel_spot_requests.assert_called_once_with(['r-456'])


@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
@patch('redis.StrictRedis')
@patch('fasteners.InterProcessLock', new=Mock())
@patch('ec2spotmanager.tasks._update_pool_status', new=Mock(side_effect=_mock_pool_status))
def test_pool_trim(mock_redis, mock_ec2mgr):
    """check that pool down-size trims older instances until we meet the requirement"""
    # ensure EC2Manager returns a request ID
    class _MockInstance(boto.ec2.instance.Instance):
        @property
        def state_code(self):
            return INSTANCE_STATE['running']
    boto_instances = [_MockInstance(), _MockInstance(), _MockInstance()]
    boto_instances[0].id = 'i-123'
    boto_instances[0].public_dns_name = 'fm-test1.fuzzing.allizom.com'
    boto_instances[1].id = 'i-456'
    boto_instances[1].public_dns_name = 'fm-test2.fuzzing.allizom.com'
    boto_instances[2].id = 'i-789'
    boto_instances[2].public_dns_name = 'fm-test3.fuzzing.allizom.com'

    def _find(*args, **kwds):
        if "instance_ids" in kwds:
            return [instance for instance in boto_instances if instance.id in kwds["instance_ids"]]
        return list(boto_instances)
    mock_ec2mgr.return_value.find.side_effect = _find

    # set-up redis mock to return price data and image name
    def _mock_redis_get(key):
        if ":blacklist:" in key:
            return None
        if ":price:" in key:
            return '{"redmond": {"mshq": [0.005]}}'
        if ":image:" in key:
            return 'warp'
        raise UncatchableException("unhandle key in mock_get(): %s" % (key,))
    mock_redis.return_value.get = Mock(side_effect=_mock_redis_get)

    # create database state
    config = create_config(name='config #1', size=4, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], ec2_max_price='0.1', userdata=b'cleverscript')
    pool = create_pool(config=config, last_cycled=timezone.now() - datetime.timedelta(seconds=300), enabled=True)
    create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                    created=timezone.now() - datetime.timedelta(seconds=100),
                    ec2_instance_id='i-123', ec2_region="redmond", ec2_zone="mshq", size=2)
    create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                    created=timezone.now() - datetime.timedelta(seconds=75),
                    ec2_instance_id='i-456', ec2_region="redmond", ec2_zone="mshq", size=1)
    create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                    created=timezone.now() - datetime.timedelta(seconds=50),
                    ec2_instance_id='i-789', ec2_region="redmond", ec2_zone="mshq", size=2)

    # call function under test
    check_instance_pool(pool.id)

    # check that laniakea calls were made
    cluster = mock_ec2mgr.return_value
    assert {call[0] for call in cluster.method_calls} == {'connect', 'find', 'terminate'}
    cluster.terminate.assert_called_once_with([boto_instances[1]])


def test_update_pool_status():
    """test that update_pool_status utility function works"""
    config = create_config(name='config #1', size=4, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], ec2_max_price='0.1', userdata=b'cleverscript')
    pool = create_pool(config=config)
    _update_pool_status(pool, 'price-too-low', 'testing')
    entry = PoolStatusEntry.objects.get()
    assert entry.msg == 'testing'
    assert entry.pool == pool
    assert not entry.isCritical


@patch('ec2spotmanager.tasks.UserData', new=Mock(side_effect=UncatchableException('UserData used')))
@patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager',
       new=Mock(side_effect=UncatchableException('EC2Manager used')))
@patch('redis.StrictRedis', new=Mock(side_effect=UncatchableException('Redis used')))
@patch('fasteners.InterProcessLock')
@patch('ec2spotmanager.tasks._update_pool_status', new=Mock(side_effect=_mock_pool_status))
def test_lock(mock_lock):
    config = create_config(name='config #1', size=4, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], ec2_max_price='0.1', userdata=b'cleverscript')
    pool = create_pool(config=config)

    mock_lock.return_value.acquire.return_value = False

    # call function under test
    check_instance_pool(pool.id)
