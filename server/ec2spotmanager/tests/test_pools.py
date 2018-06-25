# coding: utf-8
'''
Tests for Pool views.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import logging
import requests
from django.urls import reverse
import pytest
from . import assert_contains, create_config, create_pool, create_poolmsg


LOG = logging.getLogger("fm.ec2spotmanager.tests.pools")  # pylint: disable=invalid-name
pytestmark = pytest.mark.usefixtures("ec2spotmanager_test")  # pylint: disable=invalid-name
POOLS_ENTRIES_FMT = "Displaying all %d instance pools:"


@pytest.mark.parametrize(("name", "kwargs"),
                         [("ec2spotmanager:pools", None),
                          ("ec2spotmanager:poolcreate", None),
                          ("ec2spotmanager:poolview", {'poolid': 0}),
                          ("ec2spotmanager:poolprices", {'poolid': 0}),
                          ("ec2spotmanager:pooldel", {'poolid': 0}),
                          ("ec2spotmanager:poolenable", {'poolid': 0}),
                          ("ec2spotmanager:pooldisable", {'poolid': 0}),
                          ("ec2spotmanager:poolcycle", {'poolid': 0}),
                          ("ec2spotmanager:poolmsgdel", {'msgid': 0})])
def test_pools_no_login(client, name, kwargs):
    """Request without login hits the login redirect"""
    path = reverse(name, kwargs=kwargs)
    resp = client.get(path)
    assert resp.status_code == requests.codes['found']
    assert resp.url == '/login/?next=' + path


def test_pools_view_no_pools(client):
    """If no pools in db, an appropriate message is shown."""
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:pools"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    poollist = response.context['poollist']
    assert len(poollist) == 0  # 0 pools
    assert_contains(response, POOLS_ENTRIES_FMT % 0)


def test_pools_view_pool(client):
    """Create pool and see that it is shown."""
    config = create_config(name='config #1')
    pool = create_pool(config=config)
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:pools"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    poollist = response.context['poollist']
    assert len(poollist) == 1  # 1 pools
    assert_contains(response, POOLS_ENTRIES_FMT % 1)
    assert set(poollist) == {pool}


def test_pools_view_pools(client):
    """Create pool and see that it is shown."""
    configs = (create_config(name='config #1'),
               create_config(name='config #2'))
    pools = [create_pool(config=cfg) for cfg in configs]
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:pools"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    poollist = response.context['poollist']
    assert len(poollist) == 2  # 2 pools
    assert_contains(response, POOLS_ENTRIES_FMT % 2)
    assert set(poollist) == set(pools)


def test_create_pool_view_simple_get(client):
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:poolcreate"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_view_pool_view_simple_get(client):
    """No errors are thrown in template"""
    cfg = create_config(name='config #1')
    pool = create_pool(config=cfg)
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:poolview", kwargs={'poolid': pool.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_pool_prices_view_simple_get(client):
    """No errors are thrown in template"""
    cfg = create_config(name='config #1',
                        ec2_instance_types=['c4.2xlarge'])
    pool = create_pool(config=cfg)
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:poolprices", kwargs={'poolid': pool.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_delete_pool_view_simple_get(client):
    """No errors are thrown in template"""
    cfg = create_config(name='config #1')
    pool = create_pool(config=cfg)
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:pooldel", kwargs={'poolid': pool.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_enable_pool_view_simple_get(client):
    """No errors are thrown in template"""
    cfg = create_config(name='config #1')
    pool = create_pool(config=cfg)
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:poolenable", kwargs={'poolid': pool.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_disable_pool_view_simple_get(client):
    """No errors are thrown in template"""
    cfg = create_config(name='config #1')
    pool = create_pool(config=cfg)
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:pooldisable", kwargs={'poolid': pool.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_cycle_pool_view_simple_get(client):
    """No errors are thrown in template"""
    cfg = create_config(name='config #1')
    pool = create_pool(config=cfg)
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:poolcycle", kwargs={'poolid': pool.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_delete_pool_message_view_simple_get(client):
    """No errors are thrown in template"""
    cfg = create_config(name='config #1')
    pool = create_pool(config=cfg)
    msg = create_poolmsg(pool=pool)
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:poolmsgdel", kwargs={'msgid': msg.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
