from __future__ import absolute_import
import os
import time

import pytest
from django.utils import timezone
from six.moves.urllib.parse import urlsplit

from EC2Reporter.EC2Reporter import EC2Reporter, main
from ec2spotmanager.models import Instance, InstancePool
from ec2spotmanager.tests import TestCase as utils


pytest_plugins = 'server.tests'


def test_ec2reporter_help(capsys):
    '''Test that help prints without throwing'''
    with pytest.raises(SystemExit):
        main()
    _, err = capsys.readouterr()
    assert err.startswith('usage: ')


def test_ec2reporter_report(live_server, tmpdir, fm_user, monkeypatch):
    '''Test report submission'''
    monkeypatch.setattr(os.path, 'expanduser', lambda path: tmpdir.strpath)  # ensure fuzzmanager config is not used
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    # create an instance
    host = utils.create_instance('host1')

    # create a reporter
    url = urlsplit(live_server.url)
    reporter = EC2Reporter(sigCacheDir=tmpdir.mkdir('sigcache').strpath,
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

    reporter = EC2Reporter(sigCacheDir=tmpdir.join('sigcache').strpath,
                           serverHost=url.hostname,
                           serverPort=url.port,
                           serverProtocol=url.scheme,
                           serverAuthToken=fm_user.token,
                           clientId='host2')

    with pytest.raises(RuntimeError, message="Server unexpectedly responded with status code 404: Not found"):
        reporter.report('data')


def test_ec2reporter_xable(live_server, tmpdir, fm_user, monkeypatch):
    '''Test EC2Reporter enable/disable'''
    monkeypatch.setattr(os.path, 'expanduser', lambda path: tmpdir.strpath)  # ensure fuzzmanager config is not used
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    config = utils.create_config('testconfig')
    pool = utils.create_pool(config)

    # create a reporter
    url = urlsplit(live_server.url)
    reporter = EC2Reporter(sigCacheDir=tmpdir.mkdir('sigcache').strpath,
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


def test_ec2reporter_cycle(live_server, tmpdir, fm_user, monkeypatch):
    """Test EC2Reporter cycle"""
    monkeypatch.setattr(os.path, 'expanduser', lambda path: tmpdir.strpath)  # ensure fuzzmanager config is not used
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    config = utils.create_config('testconfig')
    pool = utils.create_pool(config, last_cycled=timezone.now())

    # create a reporter
    url = urlsplit(live_server.url)
    reporter = EC2Reporter(sigCacheDir=tmpdir.mkdir('sigcache').strpath,
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
