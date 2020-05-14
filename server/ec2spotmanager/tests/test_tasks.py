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
import boto.ec2
import pytest
from django.utils import timezone
from . import UncatchableException, create_config, create_instance, create_pool
from ec2spotmanager.tasks import update_requests, update_instances, cycle_and_terminate_disabled, \
    check_and_resize_pool, _terminate_instance_ids, _terminate_instance_request_ids, SPOTMGR_TAG
from ec2spotmanager.models import Instance  # PoolStatusEntry
from ec2spotmanager.CloudProvider.CloudProvider import INSTANCE_STATE, CloudProviderTemporaryFailure


LOG = logging.getLogger('fm.ec2spotmanager.tests.tasks')


pytestmark = pytest.mark.usefixtures('ec2spotmanager_test', 'raise_on_status')  # pylint: disable=invalid-name


@pytest.mark.usefixtures('mock_provider')
def test_nothing_to_do():
    """nothing is done if no pools are enabled"""

    config = create_config(name='config #1', size=1, cycle_interval=1, ec2_key_name='a', ec2_image_name='a',
                           max_price='0.1', ec2_userdata='a', ec2_allowed_regions=['a'])
    pool = create_pool(config=config)
    update_requests('prov1', 'a', pool.pk)
    update_instances('prov1', 'a')
    cycle_and_terminate_disabled('prov1', 'a')
    assert not Instance.objects.exists()


def test_bad_config():
    """invalid configs create a pool status entry"""
    config = create_config(name='config #1')
    pool = create_pool(config=config)
    with pytest.raises(UncatchableException, match=r'Configuration error \(missing: '):
        check_and_resize_pool(pool.pk)
    assert not Instance.objects.exists()

    config2 = create_config(name='config #2', parent=config)
    config.parent = config2
    config.save()
    with pytest.raises(UncatchableException, match=r'Configuration error \(cyclic\)'):
        check_and_resize_pool(pool.pk)
    assert not Instance.objects.exists()


def test_create_instance(mocker):
    """spot instance requests are created when required"""
    # set-up redis mock to return price data and image name
    def _mock_redis_get(key):
        if ":blacklist:redmond:mshq:" in key:
            return True
        if ":blacklist:" in key:
            return None
        if ":price:" in key:
            return '{"redmond": {"mshq": [0.005]}, "toronto": {"markham": [0.01]}}'
        if ":image:" in key:
            return 'warp'
        raise UncatchableException("unhandle key in mock_get(): %s" % (key,))
    mock_redis = mocker.patch('redis.StrictRedis.from_url')
    mock_redis.return_value.get = mocker.Mock(side_effect=_mock_redis_get)

    # ensure EC2Manager returns a request ID
    mocker.patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.CORES_PER_INSTANCE', new={'80286': 1})
    mock_ec2mgr = mocker.patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
    mock_ec2mgr.return_value.create_spot_requests.return_value = ('req123',)

    # create database state
    config = create_config(name='config #1', size=1, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond', 'toronto'], max_price='0.1', ec2_userdata=b'cleverscript')
    pool = create_pool(config=config, enabled=True)

    # call function under test
    check_and_resize_pool(pool.pk)

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


def test_fulfilled_spot_instance(mocker):
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
    mock_ec2mgr = mocker.patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
    mock_ec2mgr.return_value.check_spot_requests.return_value = (boto_instance,)

    # create database state
    config = create_config(name='config #1', size=1, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], max_price='0.1', ec2_userdata=b'cleverscript')
    pool = create_pool(config=config, enabled=True)
    orig = create_instance(None, pool=pool, status_code=INSTANCE_STATE['requested'],
                           ec2_instance_id='req123', ec2_region="redmond", ec2_zone="mshq")

    # call function under test
    update_requests('EC2Spot', 'redmond', pool.pk)

    # check that laniakea calls were made
    cluster = mock_ec2mgr.return_value
    assert {call[0] for call in cluster.method_calls} == {'connect', 'check_spot_requests'}

    # check that instance was updated
    instance = Instance.objects.get()
    assert instance.id == orig.id
    assert instance.hostname == 'fm-test.fuzzing.allizom.com'
    assert instance.status_code == INSTANCE_STATE["running"]
    assert instance.instance_id == 'i-123'
    assert boto_instance._test_tags == {SPOTMGR_TAG + '-Updatable': '1'}  # pylint: disable=protected-access


def test_instance_shutting_down(mocker):
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
    boto_instance1.tags = {SPOTMGR_TAG + '-Updatable': '1'}
    boto_instance2 = _MockInstance2()
    boto_instance2.id = 'i-456'
    boto_instance2.public_dns_name = 'fm-test2.fuzzing.allizom.com'
    boto_instance2.tags = {SPOTMGR_TAG + '-Updatable': '1'}
    mocker.patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.CORES_PER_INSTANCE', new={'80286': 1})
    mock_ec2mgr = mocker.patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
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
    mock_redis = mocker.patch('redis.StrictRedis.from_url')
    mock_redis.return_value.get = mocker.Mock(side_effect=_mock_redis_get)

    # ensure EC2Manager returns a request ID
    mock_ec2mgr.return_value.create_spot_requests.return_value = ('req123', 'req456')

    # create database state
    config = create_config(name='config #1', size=2, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], max_price='0.1', ec2_userdata=b'cleverscript')
    pool = create_pool(config=config, enabled=True)
    orig1 = create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                            ec2_instance_id='i-123', ec2_region="redmond", ec2_zone="mshq")
    orig2 = create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                            ec2_instance_id='i-456', ec2_region="redmond", ec2_zone="mshq")

    # call function under test
    update_instances('EC2Spot', 'redmond')
    remaining = {orig1.instance_id, orig2.instance_id}
    for old in Instance.objects.all():
        remaining.remove(old.instance_id)
        assert old.status_code in {INSTANCE_STATE['shutting-down'], INSTANCE_STATE['terminated']}
    assert not remaining

    cycle_and_terminate_disabled('EC2Spot', 'redmond')
    check_and_resize_pool(pool.pk)

    # check that laniakea calls were made
    cluster = mock_ec2mgr.return_value
    assert {call[0] for call in cluster.method_calls} == {'connect', 'create_spot_requests', 'find'}

    # check that instances were replaced
    remaining = {'req123', 'req456'}
    for new in Instance.objects.all():
        remaining.remove(new.instance_id)
        assert new.id not in {orig1.id, orig2.id}
        assert new.pool.id == pool.id
        assert new.size == 1
        assert new.status_code == INSTANCE_STATE["requested"]
    assert not remaining


def test_instance_not_updatable(mocker):
    """instances are not touched while they are not tagged Updatable"""
    # ensure EC2Manager returns a request ID
    class _MockInstance(boto.ec2.instance.Instance):
        @property
        def state_code(self):
            return INSTANCE_STATE['stopping']

    boto_instance = _MockInstance()
    boto_instance.id = 'i-123'
    boto_instance.public_dns_name = 'fm-test.fuzzing.allizom.com'
    mock_ec2mgr = mocker.patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
    mock_ec2mgr.return_value.find.return_value = (boto_instance,)

    # create database state
    config = create_config(name='config #1', size=1, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], max_price='0.1', ec2_userdata=b'cleverscript')
    pool = create_pool(config=config, enabled=True, last_cycled=timezone.now())
    orig = create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                           ec2_instance_id='i-123', ec2_region="redmond", ec2_zone="mshq")

    # call function under test
    update_instances('EC2Spot', 'redmond')
    cycle_and_terminate_disabled('EC2Spot', 'redmond')
    check_and_resize_pool(pool.pk)

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


def test_instance_price_high(mocker):
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
    mock_redis = mocker.patch('redis.StrictRedis.from_url')
    mock_redis.return_value.get = mocker.Mock(side_effect=_mock_redis_get)

    mocker.patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.CORES_PER_INSTANCE', new={'80286': 1})
    mock_ec2mgr = mocker.patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')

    # create database state
    config = create_config(name='config #1', size=1, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], max_price='0.01', ec2_userdata=b'cleverscript')
    pool = create_pool(config=config, enabled=True)

    # call function under test
    with pytest.raises(UncatchableException,
                       match="price-too-low: No allowed region was cheap enough to spawn instances"):
        check_and_resize_pool(pool.pk)

    # check that laniakea calls were made
    cluster = mock_ec2mgr.return_value
    assert not cluster.method_calls

    # check that no instances were created
    assert not Instance.objects.exists()


def test_spot_instance_blacklist(mocker):
    """check that spot requests being cancelled will result in temporary blacklisting"""
    # ensure EC2Manager returns a request ID
    class _status_code(object):
        code = 'instance-terminated-by-service'

    class _MockReq(boto.ec2.spotinstancerequest.SpotInstanceRequest):
        def __init__(self, *args, **kwds):
            super(_MockReq, self).__init__(*args, **kwds)
            self.state = 'cancelled'
            self.status = _status_code
    req = _MockReq()
    req.launch_specification = mocker.Mock()
    req.launch_specification.instance_type = '80286'
    mocker.patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.CORES_PER_INSTANCE', new={'80286': 1})
    mock_ec2mgr = mocker.patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
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
        assert ":blacklist:redmond:mshq:" in key
    mock_redis = mocker.patch('redis.StrictRedis.from_url')
    mock_redis.return_value.get = mocker.Mock(side_effect=_mock_redis_get)
    mock_redis.return_value.set = mocker.Mock(side_effect=_mock_redis_set)

    # create database state
    config = create_config(name='config #1', size=1, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], max_price='0.1', ec2_userdata=b'cleverscript')
    pool = create_pool(config=config, enabled=True)
    create_instance(None, pool=pool, status_code=INSTANCE_STATE['requested'],
                    ec2_instance_id='req123', ec2_region="redmond", ec2_zone="mshq")

    # call function under test
    # XXX: this message is inaccurate .. there were no allowed regions at all
    with pytest.raises(UncatchableException, match="temporary-failure: Spot request.* and cancelled"):
        update_requests('EC2Spot', 'redmond', pool.pk)
    update_instances('EC2Spot', 'redmond')
    with pytest.raises(UncatchableException, match="No allowed region was cheap enough to spawn instances"):
        check_and_resize_pool(pool.pk)

    # check that laniakea calls were made
    cluster = mock_ec2mgr.return_value
    assert {call[0] for call in cluster.method_calls} == {'connect', 'check_spot_requests', 'find'}

    # check that instance was updated
    assert not Instance.objects.exists()

    # check that blacklist was set in redis
    assert len(mock_redis.return_value.set.mock_calls) == 1


def test_pool_disabled(mocker):
    """check that pool disabled results in running and pending instances being terminated"""
    # ensure EC2Manager returns a request ID
    mock_ec2mgr = mocker.patch('ec2spotmanager.CloudProvider.EC2SpotCloudProvider.EC2Manager')
    mocker.patch('redis.StrictRedis.from_url')
    mock_term_instance = mocker.patch('ec2spotmanager.tasks._terminate_instance_ids')
    mock_term_request = mocker.patch('ec2spotmanager.tasks._terminate_instance_request_ids')

    # ensure EC2Manager returns a request ID
    mock_ec2mgr.return_value.create_spot_requests.return_value = ('req123', 'req456')

    # create database state
    config = create_config(name='config #1', size=2, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], max_price='0.1', ec2_userdata=b'cleverscript')
    pool = create_pool(config=config)
    create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                    ec2_instance_id='i-123', ec2_region="redmond", ec2_zone="mshq")
    create_instance(None, pool=pool, status_code=INSTANCE_STATE['requested'],
                    ec2_instance_id='r-456', ec2_region="redmond", ec2_zone="mshq")

    # call function under test
    cycle_and_terminate_disabled('EC2Spot', 'redmond')

    # check that laniakea calls were made
    cluster = mock_ec2mgr.return_value
    assert {call[0] for call in cluster.method_calls} == set()
    mock_term_instance.delay.assert_called_once_with('EC2Spot', 'redmond', ['i-123'])
    mock_term_request.delay.assert_called_once_with('EC2Spot', 'redmond', ['r-456'])


def test_pool_trim():
    """check that pool down-size trims older instances until we meet the requirement"""
    # create database state
    config = create_config(name='config #1', size=4, cycle_interval=3600, ec2_key_name='fredsRefurbishedSshKey',
                           ec2_security_groups='mostlysecure', ec2_instance_types=['80286'], ec2_image_name='os/2',
                           ec2_allowed_regions=['redmond'], max_price='0.1', ec2_userdata=b'cleverscript')
    pool = create_pool(config=config, last_cycled=timezone.now() - datetime.timedelta(seconds=300), enabled=True)
    create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                    created=timezone.now() - datetime.timedelta(seconds=100),
                    ec2_instance_id='i-123', ec2_region="redmond", ec2_zone="mshq", size=2)
    instance = create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                               created=timezone.now() - datetime.timedelta(seconds=75),
                               ec2_instance_id='i-456', ec2_region="redmond", ec2_zone="mshq", size=1)
    create_instance(None, pool=pool, status_code=INSTANCE_STATE['running'],
                    created=timezone.now() - datetime.timedelta(seconds=50),
                    ec2_instance_id='i-789', ec2_region="redmond", ec2_zone="mshq", size=2)

    # call function under test
    # result is what would normally be passed as an arg to terminate_instances()
    result = check_and_resize_pool(pool.pk)
    assert result == [instance.pk]


@pytest.mark.parametrize("term_task,provider_func", [(_terminate_instance_ids, "terminate_instances"),
                                                     (_terminate_instance_request_ids, "cancel_requests")])
def test_terminate(mocker, term_task, provider_func):
    """check that terminate instances task works properly"""
    fake_provider_cls = mocker.patch('ec2spotmanager.tasks.CloudProvider')
    fake_provider = fake_provider_cls.get_instance.return_value = mocker.Mock()
    term_task('provider', 'region', ['inst1', 'inst2'])
    fake_provider_cls.get_instance.assert_called_once_with('provider')
    provider_func = getattr(fake_provider, provider_func)
    provider_func.assert_called_once_with({'region': ['inst1', 'inst2']})

    provider_func.side_effect = CloudProviderTemporaryFailure('blah')
    with pytest.raises(CloudProviderTemporaryFailure,
                       match=r'CloudProviderTemporaryFailure: blah \(temporary-failure\)'):
        term_task('provider', 'region', [])

    provider_func.side_effect = Exception('blah')
    with pytest.raises(Exception, match=r'blah'):
        term_task('provider', 'region', [])
