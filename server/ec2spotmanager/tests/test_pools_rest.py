# coding: utf-8
'''
Tests for Pools rest api.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import json
import logging
import pytest
import requests
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from ec2spotmanager.models import InstancePool
from . import create_config, create_pool


LOG = logging.getLogger("fm.ec2spotmanager.tests.pools.rest")  # pylint: disable=invalid-name
pytestmark = pytest.mark.usefixtures("ec2spotmanager_test")  # pylint: disable=invalid-name


def test_rest_pool_cycle_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = '/ec2spotmanager/rest/pool/1/cycle/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.put(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.patch(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.delete(url, {}).status_code == requests.codes['unauthorized']


def test_rest_pool_cycle_no_perm(api_client):
    """must yield forbidden without permission"""
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    url = '/ec2spotmanager/rest/pool/1/cycle/'
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url, {}).status_code == requests.codes['forbidden']
    assert api_client.put(url, {}).status_code == requests.codes['forbidden']
    assert api_client.patch(url, {}).status_code == requests.codes['forbidden']
    assert api_client.delete(url, {}).status_code == requests.codes['forbidden']


def test_rest_pool_cycle_patch(api_client):
    """patch should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.patch('/ec2spotmanager/rest/pool/1/cycle/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_cycle_post(api_client):
    """post should reset last_cycled"""
    config = create_config('testconfig')
    pool = create_pool(config, last_cycled=timezone.now())
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/ec2spotmanager/rest/pool/%d/cycle/' % pool.pk)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['not_acceptable']
    pool.isEnabled = True
    pool.save()
    resp = api_client.post('/ec2spotmanager/rest/pool/%d/cycle/' % pool.pk)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    pool = InstancePool.objects.get(pk=pool.pk)
    assert pool.isEnabled
    assert pool.last_cycled is None


def test_rest_pool_cycle_put(api_client):
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/ec2spotmanager/rest/pool/1/cycle/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_cycle_delete(api_client):
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/ec2spotmanager/rest/pool/1/cycle/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_cycle_get(api_client):
    """get should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/ec2spotmanager/rest/pool/1/cycle/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_enable_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = '/ec2spotmanager/rest/pool/1/enable/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.put(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.patch(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.delete(url, {}).status_code == requests.codes['unauthorized']


def test_rest_pool_enable_no_perm(api_client):
    """must yield forbidden without permission"""
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    url = '/ec2spotmanager/rest/pool/1/enable/'
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url, {}).status_code == requests.codes['forbidden']
    assert api_client.put(url, {}).status_code == requests.codes['forbidden']
    assert api_client.patch(url, {}).status_code == requests.codes['forbidden']
    assert api_client.delete(url, {}).status_code == requests.codes['forbidden']


def test_rest_pool_enable_patch(api_client):
    """patch should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.patch('/ec2spotmanager/rest/pool/1/enable/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_enable_post(api_client):
    """post should flip isEnabled"""
    config = create_config('testconfig')
    pool = create_pool(config)
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/ec2spotmanager/rest/pool/%d/enable/' % pool.pk)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    pool = InstancePool.objects.get(pk=pool.pk)
    assert pool.isEnabled
    resp = api_client.post('/ec2spotmanager/rest/pool/%d/enable/' % pool.pk)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['not_acceptable']
    pool = InstancePool.objects.get(pk=pool.pk)
    assert pool.isEnabled


def test_rest_pool_enable_put(api_client):
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/ec2spotmanager/rest/pool/1/enable/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_enable_delete(api_client):
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/ec2spotmanager/rest/pool/1/enable/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_enable_get(api_client):
    """get should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/ec2spotmanager/rest/pool/1/enable/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_disable_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = '/ec2spotmanager/rest/pool/1/disable/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.put(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.patch(url, {}).status_code == requests.codes['unauthorized']
    assert api_client.delete(url, {}).status_code == requests.codes['unauthorized']


def test_rest_pool_disable_no_perm(api_client):
    """must yield forbidden without permission"""
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    url = '/ec2spotmanager/rest/pool/1/disable/'
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url, {}).status_code == requests.codes['forbidden']
    assert api_client.put(url, {}).status_code == requests.codes['forbidden']
    assert api_client.patch(url, {}).status_code == requests.codes['forbidden']
    assert api_client.delete(url, {}).status_code == requests.codes['forbidden']


def test_rest_pool_disable_patch(api_client):
    """patch should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.patch('/ec2spotmanager/rest/pool/1/disable/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_disable_post(api_client):
    """post should flip isEnabled"""
    config = create_config('testconfig')
    pool = create_pool(config, enabled=True)
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/ec2spotmanager/rest/pool/%d/disable/' % pool.pk)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['ok']
    pool = InstancePool.objects.get(pk=pool.pk)
    assert not pool.isEnabled
    resp = api_client.post('/ec2spotmanager/rest/pool/%d/disable/' % pool.pk)
    LOG.debug(resp)
    assert resp.status_code == requests.codes['not_acceptable']
    pool = InstancePool.objects.get(pk=pool.pk)
    assert not pool.isEnabled


def test_rest_pool_disable_put(api_client):
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/ec2spotmanager/rest/pool/1/disable/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_disable_delete(api_client):
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/ec2spotmanager/rest/pool/1/disable/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_disable_get(api_client):
    """get should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/ec2spotmanager/rest/pool/1/disable/')
    LOG.debug(resp)
    assert resp.status_code == requests.codes['method_not_allowed']


@pytest.mark.xfail
class TestRestPoolChartDetailed(object):

    @staticmethod
    def test_rest_pool_chart_detailed_no_auth(api_client):
        """must yield forbidden without authentication"""
        url = reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1})
        assert api_client.get(url).status_code == requests.codes['unauthorized']
        assert api_client.post(url, {}).status_code == requests.codes['unauthorized']
        assert api_client.put(url, {}).status_code == requests.codes['unauthorized']
        assert api_client.patch(url, {}).status_code == requests.codes['unauthorized']
        assert api_client.delete(url, {}).status_code == requests.codes['unauthorized']

    @staticmethod
    def test_rest_pool_chart_detailed_no_perm(api_client):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        api_client.force_authenticate(user=user)
        url = reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1})
        assert api_client.get(url).status_code == requests.codes['forbidden']
        assert api_client.post(url, {}).status_code == requests.codes['forbidden']
        assert api_client.put(url, {}).status_code == requests.codes['forbidden']
        assert api_client.patch(url, {}).status_code == requests.codes['forbidden']
        assert api_client.delete(url, {}).status_code == requests.codes['forbidden']

    @staticmethod
    def test_rest_pool_chart_detailed_patch(api_client):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        api_client.force_authenticate(user=user)
        resp = api_client.patch(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1}))
        LOG.debug(resp)
        assert resp.status_code == requests.codes['method_not_allowed']

    @staticmethod
    def test_rest_pool_chart_detailed_post(api_client):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        api_client.force_authenticate(user=user)
        resp = api_client.post(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1}))
        LOG.debug(resp)
        assert resp.status_code == requests.codes['method_not_allowed']

    @staticmethod
    def test_rest_pool_chart_detailed_put(api_client):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        api_client.force_authenticate(user=user)
        resp = api_client.put(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1}))
        LOG.debug(resp)
        assert resp.status_code == requests.codes['method_not_allowed']

    @staticmethod
    def test_rest_pool_chart_detailed_delete(api_client):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        api_client.force_authenticate(user=user)
        resp = api_client.delete(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': 1}))
        LOG.debug(resp)
        assert resp.status_code == requests.codes['method_not_allowed']

    @staticmethod
    def test_rest_pool_chart_detailed_get(api_client):
        """get should not be allowed"""
        pool = create_pool(create_config('testconfig', size=1))
        user = User.objects.get(username='test')
        api_client.force_authenticate(user=user)
        resp = api_client.get(reverse('ec2spotmanager:line_chart_json_detailed', kwargs={'poolid': pool.pk}))
        LOG.debug(resp)
        assert resp.status_code == requests.codes['ok']
        resp = json.loads(resp.content.decode('utf-8'))
        assert set(resp.keys()), {'poolid', 'labels', 'datasets', 'options' == 'view'}


@pytest.mark.xfail
class TestRestPoolChartAccumulated(object):

    @staticmethod
    def test_rest_pool_chart_accumulated_no_auth(api_client):
        """must yield forbidden without authentication"""
        url = reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1})
        assert api_client.get(url).status_code == requests.codes['unauthorized']
        assert api_client.post(url, {}).status_code == requests.codes['unauthorized']
        assert api_client.put(url, {}).status_code == requests.codes['unauthorized']
        assert api_client.patch(url, {}).status_code == requests.codes['unauthorized']
        assert api_client.delete(url, {}).status_code == requests.codes['unauthorized']

    @staticmethod
    def test_rest_pool_chart_accumulated_no_perm(api_client):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        api_client.force_authenticate(user=user)
        url = reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1})
        assert api_client.get(url).status_code == requests.codes['forbidden']
        assert api_client.post(url, {}).status_code == requests.codes['forbidden']
        assert api_client.put(url, {}).status_code == requests.codes['forbidden']
        assert api_client.patch(url, {}).status_code == requests.codes['forbidden']
        assert api_client.delete(url, {}).status_code == requests.codes['forbidden']

    @staticmethod
    def test_rest_pool_chart_accumulated_patch(api_client):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        api_client.force_authenticate(user=user)
        resp = api_client.patch(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1}))
        LOG.debug(resp)
        assert resp.status_code == requests.codes['method_not_allowed']

    @staticmethod
    def test_rest_pool_chart_accumulated_post(api_client):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        api_client.force_authenticate(user=user)
        resp = api_client.post(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1}))
        LOG.debug(resp)
        assert resp.status_code == requests.codes['method_not_allowed']

    @staticmethod
    def test_rest_pool_chart_accumulated_put(api_client):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        api_client.force_authenticate(user=user)
        resp = api_client.put(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1}))
        LOG.debug(resp)
        assert resp.status_code == requests.codes['method_not_allowed']

    @staticmethod
    def test_rest_pool_chart_accumulated_delete(api_client):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        api_client.force_authenticate(user=user)
        resp = api_client.delete(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': 1}))
        LOG.debug(resp)
        assert resp.status_code == requests.codes['method_not_allowed']

    @staticmethod
    def test_rest_pool_chart_accumulated_get(api_client):
        """get should be allowed"""
        pool = create_pool(create_config('testconfig'))
        user = User.objects.get(username='test')
        api_client.force_authenticate(user=user)
        resp = api_client.get(reverse('ec2spotmanager:line_chart_json_accumulated', kwargs={'poolid': pool.pk}))
        LOG.debug(resp)
        assert resp.status_code == requests.codes['ok']
        resp = json.loads(resp.content.decode('utf-8'))
        assert set(resp.keys()), {'poolid', 'labels', 'datasets', 'options' == 'view'}
