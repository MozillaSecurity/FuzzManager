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
from rest_framework.test import APITestCase  # APIRequestFactory

from . import TestCase


log = logging.getLogger("fm.ec2spotmanager.tests.configs.rest")  # pylint: disable=invalid-name


class RestPoolConfigurationsTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/ec2spotmanager/rest/configurations/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url).status_code, requests.codes['unauthorized'])

    def test_no_perm(self):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        self.client.force_authenticate(user=user)
        url = '/ec2spotmanager/rest/configurations/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.post(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.put(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.patch(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.delete(url).status_code, requests.codes['forbidden'])

    def test_auth(self):
        """test that authenticated requests work"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/configurations/')
        self.assertEqual(resp.status_code, requests.codes['ok'])

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/ec2spotmanager/rest/configurations/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/ec2spotmanager/rest/configurations/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_post(self):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/ec2spotmanager/rest/configurations/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/ec2spotmanager/rest/configurations/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_list_no_configs(self):
        """test empty response to config list"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/configurations/')
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(set(resp.keys()), {'count', 'next', 'previous', 'results'})
        self.assertEqual(resp['count'], 0)
        self.assertEqual(resp['next'], None)
        self.assertEqual(resp['previous'], None)
        resp = resp['results']
        self.assertEqual(len(resp), 0)

    def test_list_configs(self):
        """test that configs can be listed"""
        cfg1 = self.create_config(name='config #1',
                                  size=1234567,
                                  cycle_interval=7654321,
                                  ec2_key_name='key #1',
                                  ec2_security_groups=['group #1'],
                                  ec2_instance_types=['machine #1'],
                                  ec2_image_name='ami #1',
                                  userdata_macros={'yup': '123', 'nope': '456'},
                                  ec2_allowed_regions=['nowhere'],
                                  ec2_max_price=0.01,
                                  ec2_tags={'good': 'true', 'bad': 'false'},
                                  ec2_raw_config={'hello': 'world'})
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/configurations/')
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content.decode('utf-8'))
        self.assertEqual(set(resp.keys()), {'count', 'next', 'previous', 'results'})
        self.assertEqual(resp['count'], 1)
        self.assertEqual(resp['next'], None)
        self.assertEqual(resp['previous'], None)
        resp = resp['results']
        self.assertEqual(len(resp), 1)
        assert set(resp[0].keys()) == {
            'cycle_interval', 'ec2_allowed_regions', 'ec2_allowed_regions_override', 'ec2_image_name',
            'ec2_instance_types', 'ec2_instance_types_override', 'ec2_key_name', 'ec2_max_price', 'ec2_raw_config',
            'ec2_raw_config_override', 'ec2_security_groups', 'ec2_security_groups_override', 'ec2_tags',
            'ec2_tags_override', 'id', 'name', 'parent', 'size', 'userdata_macros', 'userdata_macros_override',
        }
        assert resp[0]['cycle_interval'] == 7654321
        assert resp[0]['ec2_allowed_regions'] == ['nowhere']
        assert not resp[0]['ec2_allowed_regions_override']
        assert resp[0]['ec2_image_name'] == 'ami #1'
        assert resp[0]['ec2_instance_types'] == ['machine #1']
        assert not resp[0]['ec2_instance_types_override']
        assert resp[0]['ec2_key_name'] == 'key #1'
        assert resp[0]['ec2_max_price'] == 0.01
        assert resp[0]['ec2_raw_config'] == {'hello': 'world'}
        assert not resp[0]['ec2_raw_config_override']
        assert resp[0]['ec2_security_groups'] == ['group #1']
        assert not resp[0]['ec2_security_groups_override']
        assert resp[0]['ec2_tags'] == {'good': 'true', 'bad': 'false'}
        assert not resp[0]['ec2_tags_override']
        assert resp[0]['id'] == cfg1.pk
        assert resp[0]['name'] == 'config #1'
        assert resp[0]['parent'] is None
        assert resp[0]['size'] == 1234567
        assert resp[0]['userdata_macros'] == {'yup': '123', 'nope': '456'}
        assert not resp[0]['userdata_macros_override']


class RestPoolConfigurationTests(APITestCase, TestCase):

    def test_no_auth(self):
        """must yield forbidden without authentication"""
        url = '/ec2spotmanager/rest/configurations/1/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.post(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.put(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.patch(url).status_code, requests.codes['unauthorized'])
        self.assertEqual(self.client.delete(url).status_code, requests.codes['unauthorized'])

    def test_no_perm(self):
        """must yield forbidden without permission"""
        user = User.objects.get(username='test-noperm')
        self.client.force_authenticate(user=user)
        url = '/ec2spotmanager/rest/configurations/1/'
        self.assertEqual(self.client.get(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.post(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.put(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.patch(url).status_code, requests.codes['forbidden'])
        self.assertEqual(self.client.delete(url).status_code, requests.codes['forbidden'])

    def test_auth(self):
        """test that authenticated requests work"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/configurations/')
        self.assertEqual(resp.status_code, requests.codes['ok'])

    def test_delete(self):
        """delete should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.delete('/ec2spotmanager/rest/configurations/1/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_patch(self):
        """patch should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.patch('/ec2spotmanager/rest/configurations/1/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_put(self):
        """put should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.put('/ec2spotmanager/rest/configurations/1/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_post(self):
        """post should not be allowed"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.post('/ec2spotmanager/rest/configurations/1/')
        self.assertEqual(resp.status_code, requests.codes['method_not_allowed'])

    def test_get_0(self):
        """test that non-existent PoolConfiguration is error"""
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/configurations/1/')
        self.assertEqual(resp.status_code, requests.codes['not_found'])

    def test_get_1(self):
        """test that individual PoolConfiguration can be fetched"""
        cfg1 = self.create_config(name='config #1',
                                  size=1234567,
                                  cycle_interval=7654321,
                                  ec2_key_name='key #1',
                                  ec2_security_groups=['group #1'],
                                  ec2_instance_types=['machine #1'],
                                  ec2_image_name='ami #1',
                                  userdata_macros={'yup': '123', 'nope': '456'},
                                  ec2_allowed_regions=['nowhere'],
                                  ec2_max_price=0.01,
                                  ec2_tags={'good': 'true', 'bad': 'false'},
                                  ec2_raw_config={'hello': 'world'})
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/configurations/%d/' % cfg1.pk)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content.decode('utf-8'))
        assert set(resp.keys()) == {
            'cycle_interval', 'ec2_allowed_regions', 'ec2_allowed_regions_override', 'ec2_image_name',
            'ec2_instance_types', 'ec2_instance_types_override', 'ec2_key_name', 'ec2_max_price', 'ec2_raw_config',
            'ec2_raw_config_override', 'ec2_security_groups', 'ec2_security_groups_override', 'ec2_tags',
            'ec2_tags_override', 'id', 'name', 'parent', 'size', 'userdata_macros', 'userdata_macros_override',
        }
        assert resp['cycle_interval'] == 7654321
        assert resp['ec2_allowed_regions'] == ['nowhere']
        assert not resp['ec2_allowed_regions_override']
        assert resp['ec2_image_name'] == 'ami #1'
        assert resp['ec2_instance_types'] == ['machine #1']
        assert not resp['ec2_instance_types_override']
        assert resp['ec2_key_name'] == 'key #1'
        assert resp['ec2_max_price'] == 0.01
        assert resp['ec2_raw_config'] == {'hello': 'world'}
        assert not resp['ec2_raw_config_override']
        assert resp['ec2_security_groups'] == ['group #1']
        assert not resp['ec2_security_groups_override']
        assert resp['ec2_tags'] == {'good': 'true', 'bad': 'false'}
        assert not resp['ec2_tags_override']
        assert resp['id'] == cfg1.pk
        assert resp['name'] == 'config #1'
        assert resp['parent'] is None
        assert resp['size'] == 1234567
        assert resp['userdata_macros'] == {'yup': '123', 'nope': '456'}
        assert not resp['userdata_macros_override']

    def test_get_sub(self):
        """test that inherited Signature can be fetched unflattened"""
        cfg1 = self.create_config(name='config #1',
                                  size=1234567,
                                  cycle_interval=7654321,
                                  ec2_key_name='key #1',
                                  ec2_security_groups=['group #1'],
                                  ec2_instance_types=['machine #1'],
                                  ec2_image_name='ami #1',
                                  userdata_macros={'yup': '123', 'nope': '456'},
                                  ec2_allowed_regions=['nowhere'],
                                  ec2_max_price=0.01,
                                  ec2_tags={'good': 'true', 'bad': 'false'},
                                  ec2_raw_config={'hello': 'world'})
        cfg2 = self.create_config(name='config #2', parent=cfg1)
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/configurations/%d/' % cfg2.id)
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content.decode('utf-8'))
        assert set(resp.keys()) == {
            'cycle_interval', 'ec2_allowed_regions', 'ec2_allowed_regions_override', 'ec2_image_name',
            'ec2_instance_types', 'ec2_instance_types_override', 'ec2_key_name', 'ec2_max_price', 'ec2_raw_config',
            'ec2_raw_config_override', 'ec2_security_groups', 'ec2_security_groups_override', 'ec2_tags',
            'ec2_tags_override', 'id', 'name', 'parent', 'size', 'userdata_macros', 'userdata_macros_override',
        }
        assert resp['cycle_interval'] is None
        assert resp['ec2_allowed_regions'] is None
        assert not resp['ec2_allowed_regions_override']
        assert resp['ec2_image_name'] is None
        assert resp['ec2_instance_types'] is None
        assert not resp['ec2_instance_types_override']
        assert resp['ec2_key_name'] is None
        assert resp['ec2_max_price'] is None
        assert resp['ec2_raw_config'] is None
        assert not resp['ec2_raw_config_override']
        assert resp['ec2_security_groups'] is None
        assert not resp['ec2_security_groups_override']
        assert resp['ec2_tags'] is None
        assert not resp['ec2_tags_override']
        assert resp['id'] == cfg2.pk
        assert resp['name'] == 'config #2'
        assert resp['parent'] == cfg1.pk
        assert resp['size'] is None
        assert resp['userdata_macros'] is None
        assert not resp['userdata_macros_override']

    def test_get_sub_flat(self):
        """test that inherited Signature can be fetched flattened"""
        cfg1 = self.create_config(name='config #1',
                                  size=1234567,
                                  cycle_interval=7654321,
                                  ec2_key_name='key #1',
                                  ec2_security_groups=['group #1'],
                                  ec2_instance_types=['machine #1'],
                                  ec2_image_name='ami #1',
                                  userdata_macros={'yup': '123', 'nope': '456'},
                                  ec2_allowed_regions=['nowhere'],
                                  ec2_max_price=0.01,
                                  ec2_tags={'good': 'true', 'bad': 'false'},
                                  ec2_raw_config={'hello': 'world'})
        cfg2 = self.create_config(name='config #2',
                                  userdata_macros={'ok': '789'},
                                  ec2_tags={'key': 'value'},
                                  parent=cfg1)
        cfg2.ec2_tags_override = True
        cfg2.save()
        user = User.objects.get(username='test')
        self.client.force_authenticate(user=user)
        resp = self.client.get('/ec2spotmanager/rest/configurations/%d/' % cfg2.id, {'flatten': '1'})
        self.assertEqual(resp.status_code, requests.codes['ok'])
        resp = json.loads(resp.content.decode('utf-8'))
        assert set(resp.keys()) == {
            'cycle_interval', 'ec2_allowed_regions', 'ec2_allowed_regions_override', 'ec2_image_name',
            'ec2_instance_types', 'ec2_instance_types_override', 'ec2_key_name', 'ec2_max_price', 'ec2_raw_config',
            'ec2_raw_config_override', 'ec2_security_groups', 'ec2_security_groups_override', 'ec2_tags',
            'ec2_tags_override', 'id', 'name', 'parent', 'size', 'userdata_macros', 'userdata_macros_override',
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
        assert resp['ec2_max_price'] == 0.01
        assert resp['ec2_raw_config'] == {'hello': 'world'}
        assert not resp['ec2_raw_config_override']
        assert resp['ec2_security_groups'] == ['group #1']
        assert not resp['ec2_security_groups_override']
        assert resp['ec2_tags'] == {'key': 'value'}
        assert resp['ec2_tags_override']
        assert resp['name'] == 'config #2'
        assert resp['size'] == 1234567
        assert resp['userdata_macros'] == {'yup': '123', 'nope': '456', 'ok': '789'}
        assert not resp['userdata_macros_override']
