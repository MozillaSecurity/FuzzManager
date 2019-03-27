from __future__ import absolute_import

import pytest
from django.utils import timezone
from six.moves.urllib.parse import urlsplit

from EC2Reporter.EC2Reporter import EC2Reporter, main
from ec2spotmanager.models import Instance, InstancePool
from ec2spotmanager.tests import create_config, create_instance, create_pool

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


pytestmark = pytest.mark.django_db(transaction=True)
pytest_plugins = 'server.tests'


def test_ec2reporter_help(capsys):
    '''Test that help prints without throwing'''
    with pytest.raises(SystemExit):
        main()
    _, err = capsys.readouterr()
    assert err.startswith('usage: ')


@patch('os.path.expanduser')
@patch('time.sleep', new=Mock())
def test_ec2reporter_report(mock_expanduser, live_server, tmp_path, fm_user):
    '''Test report submission'''
    mock_expanduser.side_effect = lambda path: str(tmp_path)  # ensure fuzzmanager config is not used

    # create an instance
    host = create_instance('host1')

    # create a reporter
    url = urlsplit(live_server.url)
    sigcache_path = tmp_path / 'sigcache'
    sigcache_path.mkdir()
    reporter = EC2Reporter(sigCacheDir=str(sigcache_path),
                           serverHost=url.hostname,
                           serverPort=url.port,
                           serverProtocol=url.scheme,
                           serverAuthToken=fm_user.token,
                           clientId='host1')

    reporter.report('data')
    host = Instance.objects.get(pk=host.pk)  # re-read
    assert host.status_data == 'data'

    reporter.report(None)
    host = Instance.objects.get(pk=host.pk)  # re-read
    assert host.status_data is None

    reporter = EC2Reporter(sigCacheDir=str(sigcache_path),
                           serverHost=url.hostname,
                           serverPort=url.port,
                           serverProtocol=url.scheme,
                           serverAuthToken=fm_user.token,
                           clientId='host2')

    with pytest.raises(RuntimeError, message="Server unexpectedly responded with status code 404: Not found"):
        reporter.report('data')


@patch('os.path.expanduser')
@patch('time.sleep', new=Mock())
def test_ec2reporter_xable(mock_expanduser, live_server, tmp_path, fm_user):
    '''Test EC2Reporter enable/disable'''
    mock_expanduser.side_effect = lambda path: str(tmp_path)  # ensure fuzzmanager config is not used

    config = create_config('testconfig')
    pool = create_pool(config)

    # create a reporter
    url = urlsplit(live_server.url)
    sigcache_path = tmp_path / 'sigcache'
    sigcache_path.mkdir()
    reporter = EC2Reporter(sigCacheDir=str(sigcache_path),
                           serverHost=url.hostname,
                           serverPort=url.port,
                           serverProtocol=url.scheme,
                           serverAuthToken=fm_user.token,
                           clientId='host1')

    reporter.enable(pool.pk)
    pool = InstancePool.objects.get(pk=pool.pk)  # re-read
    assert pool.isEnabled

    with pytest.raises(RuntimeError, message="Server unexpectedly responded with status code 405: Not acceptable"):
        reporter.enable(pool.pk)
    pool = InstancePool.objects.get(pk=pool.pk)  # re-read
    assert pool.isEnabled

    reporter.disable(pool.pk)
    pool = InstancePool.objects.get(pk=pool.pk)  # re-read
    assert not pool.isEnabled

    with pytest.raises(RuntimeError, message="Server unexpectedly responded with status code 405: Not acceptable"):
        reporter.disable(pool.pk)
    pool = InstancePool.objects.get(pk=pool.pk)  # re-read
    assert not pool.isEnabled


@patch('os.path.expanduser')
@patch('time.sleep', new=Mock())
def test_ec2reporter_cycle(mock_expanduser, live_server, tmp_path, fm_user):
    """Test EC2Reporter cycle"""
    mock_expanduser.side_effect = lambda path: str(tmp_path)  # ensure fuzzmanager config is not used

    config = create_config('testconfig')
    pool = create_pool(config, last_cycled=timezone.now())

    # create a reporter
    url = urlsplit(live_server.url)
    sigcache_path = tmp_path / 'sigcache'
    sigcache_path.mkdir()
    reporter = EC2Reporter(sigCacheDir=str(sigcache_path),
                           serverHost=url.hostname,
                           serverPort=url.port,
                           serverProtocol=url.scheme,
                           serverAuthToken=fm_user.token,
                           clientId='host1')

    with pytest.raises(RuntimeError, message="Server unexpectedly responded with status code 405: Not acceptable"):
        reporter.cycle(pool.pk)

    pool.isEnabled = True
    pool.save()
    reporter.cycle(pool.pk)
    pool = InstancePool.objects.get(pk=pool.pk)  # re-read
    assert pool.isEnabled
    assert pool.last_cycled is None
