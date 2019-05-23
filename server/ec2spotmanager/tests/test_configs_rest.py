# coding: utf-8
'''
Tests for PoolConfigurations REST API.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import json
import logging
import requests
from django.contrib.auth.models import User
import pytest
from . import create_config


LOG = logging.getLogger("fm.ec2spotmanager.tests.configs.rest")  # pylint: disable=invalid-name
pytestmark = pytest.mark.usefixtures("ec2spotmanager_test")  # pylint: disable=invalid-name


def test_rest_pool_configs_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = '/ec2spotmanager/rest/configurations/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url).status_code == requests.codes['unauthorized']
    assert api_client.put(url).status_code == requests.codes['unauthorized']
    assert api_client.patch(url).status_code == requests.codes['unauthorized']
    assert api_client.delete(url).status_code == requests.codes['unauthorized']


def test_rest_pool_configs_no_perm(api_client):
    """must yield forbidden without permission"""
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    url = '/ec2spotmanager/rest/configurations/'
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url).status_code == requests.codes['forbidden']
    assert api_client.put(url).status_code == requests.codes['forbidden']
    assert api_client.patch(url).status_code == requests.codes['forbidden']
    assert api_client.delete(url).status_code == requests.codes['forbidden']


def test_rest_pool_configs_auth(api_client):
    """test that authenticated requests work"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/ec2spotmanager/rest/configurations/')
    assert resp.status_code == requests.codes['ok']


def test_rest_pool_configs_patch(api_client):
    """patch should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.patch('/ec2spotmanager/rest/configurations/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_configs_put(api_client):
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/ec2spotmanager/rest/configurations/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_configs_post(api_client):
    """post should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/ec2spotmanager/rest/configurations/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_configs_delete(api_client):
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/ec2spotmanager/rest/configurations/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_configs_list_no_configs(api_client):
    """test empty response to config list"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/ec2spotmanager/rest/configurations/')
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()), {'count', 'next', 'previous' == 'results'}
    assert resp['count'] == 0
    assert resp['next'] is None
    assert resp['previous'] is None
    resp = resp['results']
    assert len(resp) == 0


def test_rest_pool_configs_list_configs(api_client):
    """test that configs can be listed"""
    cfg1 = create_config(name='config #1',
                         size=1234567,
                         cycle_interval=7654321,
                         ec2_key_name='key #1',
                         ec2_security_groups=['group #1'],
                         ec2_instance_types=['machine #1'],
                         ec2_image_name='ami #1',
                         ec2_userdata_macros={'yup': '123', 'nope': '456'},
                         ec2_allowed_regions=['nowhere'],
                         max_price=0.01,
                         instance_tags={'good': 'true', 'bad': 'false'},
                         ec2_raw_config={'hello': 'world'})
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/ec2spotmanager/rest/configurations/')
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()), {'count', 'next', 'previous' == 'results'}
    assert resp['count'] == 1
    assert resp['next'] is None
    assert resp['previous'] is None
    resp = resp['results']
    assert len(resp) == 1
    assert set(resp[0].keys()) == {
        'cycle_interval', 'ec2_allowed_regions', 'ec2_allowed_regions_override', 'ec2_image_name',
        'ec2_instance_types', 'ec2_instance_types_override', 'ec2_key_name', 'max_price', 'ec2_raw_config',
        'ec2_raw_config_override', 'ec2_security_groups', 'ec2_security_groups_override', 'instance_tags',
        'instance_tags_override', 'gce_container_name', 'gce_disk_size', 'gce_env', 'gce_env_override',
        'gce_image_name', 'gce_machine_types', 'gce_machine_types_override', 'id', 'name', 'parent', 'size',
        'ec2_userdata_macros', 'ec2_userdata_macros_override', 'gce_raw_config', 'gce_args', 'gce_cmd_override',
        'gce_cmd', 'gce_docker_privileged', 'gce_env_include_macros', 'gce_args_override', 'gce_raw_config_override',
    }
    assert resp[0]['cycle_interval'] == 7654321
    assert resp[0]['ec2_allowed_regions'] == ['nowhere']
    assert not resp[0]['ec2_allowed_regions_override']
    assert resp[0]['ec2_image_name'] == 'ami #1'
    assert resp[0]['ec2_instance_types'] == ['machine #1']
    assert not resp[0]['ec2_instance_types_override']
    assert resp[0]['ec2_key_name'] == 'key #1'
    assert resp[0]['max_price'] == 0.01
    assert resp[0]['ec2_raw_config'] == {'hello': 'world'}
    assert not resp[0]['ec2_raw_config_override']
    assert resp[0]['ec2_security_groups'] == ['group #1']
    assert not resp[0]['ec2_security_groups_override']
    assert resp[0]['instance_tags'] == {'good': 'true', 'bad': 'false'}
    assert not resp[0]['instance_tags_override']
    assert resp[0]['id'] == cfg1.pk
    assert resp[0]['name'] == 'config #1'
    assert resp[0]['parent'] is None
    assert resp[0]['size'] == 1234567
    assert resp[0]['ec2_userdata_macros'] == {'yup': '123', 'nope': '456'}
    assert not resp[0]['ec2_userdata_macros_override']


def test_rest_pool_config_no_auth(api_client):
    """must yield forbidden without authentication"""
    url = '/ec2spotmanager/rest/configurations/1/'
    assert api_client.get(url).status_code == requests.codes['unauthorized']
    assert api_client.post(url).status_code == requests.codes['unauthorized']
    assert api_client.put(url).status_code == requests.codes['unauthorized']
    assert api_client.patch(url).status_code == requests.codes['unauthorized']
    assert api_client.delete(url).status_code == requests.codes['unauthorized']


def test_rest_pool_config_no_perm(api_client):
    """must yield forbidden without permission"""
    user = User.objects.get(username='test-noperm')
    api_client.force_authenticate(user=user)
    url = '/ec2spotmanager/rest/configurations/1/'
    assert api_client.get(url).status_code == requests.codes['forbidden']
    assert api_client.post(url).status_code == requests.codes['forbidden']
    assert api_client.put(url).status_code == requests.codes['forbidden']
    assert api_client.patch(url).status_code == requests.codes['forbidden']
    assert api_client.delete(url).status_code == requests.codes['forbidden']


def test_rest_pool_config_auth(api_client):
    """test that authenticated requests work"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/ec2spotmanager/rest/configurations/')
    assert resp.status_code == requests.codes['ok']


def test_rest_pool_config_delete(api_client):
    """delete should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.delete('/ec2spotmanager/rest/configurations/1/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_config_patch(api_client):
    """patch should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.patch('/ec2spotmanager/rest/configurations/1/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_config_put(api_client):
    """put should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.put('/ec2spotmanager/rest/configurations/1/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_config_post(api_client):
    """post should not be allowed"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.post('/ec2spotmanager/rest/configurations/1/')
    assert resp.status_code == requests.codes['method_not_allowed']


def test_rest_pool_config_get_0(api_client):
    """test that non-existent PoolConfiguration is error"""
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/ec2spotmanager/rest/configurations/1/')
    assert resp.status_code == requests.codes['not_found']


def test_rest_pool_config_get_1(api_client):
    """test that individual PoolConfiguration can be fetched"""
    cfg1 = create_config(name='config #1',
                         size=1234567,
                         cycle_interval=7654321,
                         ec2_key_name='key #1',
                         ec2_security_groups=['group #1'],
                         ec2_instance_types=['machine #1'],
                         ec2_image_name='ami #1',
                         ec2_userdata_macros={'yup': '123', 'nope': '456'},
                         ec2_allowed_regions=['nowhere'],
                         max_price=0.01,
                         instance_tags={'good': 'true', 'bad': 'false'},
                         ec2_raw_config={'hello': 'world'})
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/ec2spotmanager/rest/configurations/%d/' % cfg1.pk)
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()) == {
        'cycle_interval', 'ec2_allowed_regions', 'ec2_allowed_regions_override', 'ec2_image_name',
        'ec2_instance_types', 'ec2_instance_types_override', 'ec2_key_name', 'max_price', 'ec2_raw_config',
        'ec2_raw_config_override', 'ec2_security_groups', 'ec2_security_groups_override', 'instance_tags',
        'instance_tags_override', 'gce_container_name', 'gce_disk_size', 'gce_env', 'gce_env_override',
        'gce_image_name', 'gce_machine_types', 'gce_machine_types_override', 'id', 'name', 'parent', 'size',
        'ec2_userdata_macros', 'ec2_userdata_macros_override', 'gce_raw_config', 'gce_args', 'gce_cmd_override',
        'gce_cmd', 'gce_docker_privileged', 'gce_env_include_macros', 'gce_args_override', 'gce_raw_config_override',
    }
    assert resp['cycle_interval'] == 7654321
    assert resp['ec2_allowed_regions'] == ['nowhere']
    assert not resp['ec2_allowed_regions_override']
    assert resp['ec2_image_name'] == 'ami #1'
    assert resp['ec2_instance_types'] == ['machine #1']
    assert not resp['ec2_instance_types_override']
    assert resp['ec2_key_name'] == 'key #1'
    assert resp['max_price'] == 0.01
    assert resp['ec2_raw_config'] == {'hello': 'world'}
    assert not resp['ec2_raw_config_override']
    assert resp['ec2_security_groups'] == ['group #1']
    assert not resp['ec2_security_groups_override']
    assert resp['instance_tags'] == {'good': 'true', 'bad': 'false'}
    assert not resp['instance_tags_override']
    assert resp['id'] == cfg1.pk
    assert resp['name'] == 'config #1'
    assert resp['parent'] is None
    assert resp['size'] == 1234567
    assert resp['ec2_userdata_macros'] == {'yup': '123', 'nope': '456'}
    assert not resp['ec2_userdata_macros_override']


def test_rest_pool_config_get_sub(api_client):
    """test that inherited Signature can be fetched unflattened"""
    cfg1 = create_config(name='config #1',
                         size=1234567,
                         cycle_interval=7654321,
                         ec2_key_name='key #1',
                         ec2_security_groups=['group #1'],
                         ec2_instance_types=['machine #1'],
                         ec2_image_name='ami #1',
                         ec2_userdata_macros={'yup': '123', 'nope': '456'},
                         ec2_allowed_regions=['nowhere'],
                         max_price=0.01,
                         instance_tags={'good': 'true', 'bad': 'false'},
                         ec2_raw_config={'hello': 'world'})
    cfg2 = create_config(name='config #2', parent=cfg1)
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/ec2spotmanager/rest/configurations/%d/' % cfg2.id)
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()) == {
        'cycle_interval', 'ec2_allowed_regions', 'ec2_allowed_regions_override', 'ec2_image_name',
        'ec2_instance_types', 'ec2_instance_types_override', 'ec2_key_name', 'max_price', 'ec2_raw_config',
        'ec2_raw_config_override', 'ec2_security_groups', 'ec2_security_groups_override', 'instance_tags',
        'instance_tags_override', 'gce_container_name', 'gce_disk_size', 'gce_env', 'gce_env_override',
        'gce_image_name', 'gce_machine_types', 'gce_machine_types_override', 'id', 'name', 'parent', 'size',
        'ec2_userdata_macros', 'ec2_userdata_macros_override', 'gce_raw_config', 'gce_args', 'gce_cmd_override',
        'gce_cmd', 'gce_docker_privileged', 'gce_env_include_macros', 'gce_args_override', 'gce_raw_config_override',
    }
    assert resp['cycle_interval'] is None
    assert resp['ec2_allowed_regions'] is None
    assert not resp['ec2_allowed_regions_override']
    assert resp['ec2_image_name'] is None
    assert resp['ec2_instance_types'] is None
    assert not resp['ec2_instance_types_override']
    assert resp['ec2_key_name'] is None
    assert resp['max_price'] is None
    assert resp['ec2_raw_config'] is None
    assert not resp['ec2_raw_config_override']
    assert resp['ec2_security_groups'] is None
    assert not resp['ec2_security_groups_override']
    assert resp['instance_tags'] is None
    assert not resp['instance_tags_override']
    assert resp['id'] == cfg2.pk
    assert resp['name'] == 'config #2'
    assert resp['parent'] == cfg1.pk
    assert resp['size'] is None
    assert resp['ec2_userdata_macros'] is None
    assert not resp['ec2_userdata_macros_override']


def test_rest_pool_config_get_sub_flat(api_client):
    """test that inherited Signature can be fetched flattened"""
    cfg1 = create_config(name='config #1',
                         size=1234567,
                         cycle_interval=7654321,
                         ec2_key_name='key #1',
                         ec2_security_groups=['group #1'],
                         ec2_instance_types=['machine #1'],
                         ec2_image_name='ami #1',
                         ec2_userdata_macros={'yup': '123', 'nope': '456'},
                         ec2_allowed_regions=['nowhere'],
                         max_price=0.01,
                         instance_tags={'good': 'true', 'bad': 'false'},
                         ec2_raw_config={'hello': 'world'},
                         gce_disk_size=8,
                         gce_image_name="cos #1",
                         gce_container_name="alpine:latest")
    cfg2 = create_config(name='config #2',
                         ec2_userdata_macros={'ok': '789'},
                         instance_tags={'key': 'value'},
                         parent=cfg1)
    cfg2.instance_tags_override = True
    cfg2.save()
    user = User.objects.get(username='test')
    api_client.force_authenticate(user=user)
    resp = api_client.get('/ec2spotmanager/rest/configurations/%d/' % cfg2.id, {'flatten': '1'})
    assert resp.status_code == requests.codes['ok']
    resp = json.loads(resp.content.decode('utf-8'))
    assert set(resp.keys()) == {
        'cycle_interval', 'ec2_allowed_regions', 'ec2_allowed_regions_override', 'ec2_image_name',
        'ec2_instance_types', 'ec2_instance_types_override', 'ec2_key_name', 'max_price', 'ec2_raw_config',
        'ec2_raw_config_override', 'ec2_security_groups', 'ec2_security_groups_override', 'instance_tags',
        'instance_tags_override', 'gce_container_name', 'gce_disk_size', 'gce_env', 'gce_env_override',
        'gce_image_name', 'gce_machine_types', 'gce_machine_types_override', 'id', 'name', 'parent', 'size',
        'ec2_userdata_macros', 'ec2_userdata_macros_override', 'gce_raw_config', 'gce_args', 'gce_cmd_override',
        'gce_cmd', 'gce_docker_privileged', 'gce_env_include_macros', 'gce_args_override', 'gce_raw_config_override',
    }
    assert resp['id'] == cfg2.pk
    assert resp['parent'] is cfg1.pk
    assert resp['cycle_interval'] == 7654321
    assert resp['ec2_allowed_regions'] == ['nowhere']
    assert not resp['ec2_allowed_regions_override']
    assert resp['ec2_image_name'] == 'ami #1'
    assert resp['ec2_instance_types'] == ['machine #1']
    assert not resp['ec2_instance_types_override']
    assert resp['ec2_key_name'] == 'key #1'
    assert resp['max_price'] == 0.01
    assert resp['ec2_raw_config'] == {'hello': 'world'}
    assert not resp['ec2_raw_config_override']
    assert resp['ec2_security_groups'] == ['group #1']
    assert not resp['ec2_security_groups_override']
    assert resp['instance_tags'] == {'key': 'value'}
    assert resp['instance_tags_override']
    assert resp['name'] == 'config #2'
    assert resp['size'] == 1234567
    assert resp['ec2_userdata_macros'] == {'yup': '123', 'nope': '456', 'ok': '789'}
    assert not resp['ec2_userdata_macros_override']
