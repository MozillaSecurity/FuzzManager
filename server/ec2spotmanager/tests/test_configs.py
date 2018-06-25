# coding: utf-8
'''
Tests for Configuration views.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import decimal
import json
import logging
import requests
from django.urls import reverse
import pytest
from ec2spotmanager.models import PoolConfiguration
from . import assert_contains, create_config


LOG = logging.getLogger("fm.ec2spotmanager.tests.configs")  # pylint: disable=invalid-name
pytestmark = pytest.mark.usefixtures("ec2spotmanager_test")  # pylint: disable=invalid-name


@pytest.mark.parametrize(("name", "kwargs"),
                         [("ec2spotmanager:configs", None),
                          ("ec2spotmanager:configcreate", None),
                          ("ec2spotmanager:configview", {'configid': 0}),
                          ("ec2spotmanager:configedit", {'configid': 0}),
                          ("ec2spotmanager:configdel", {'configid': 0})])
def test_configs_no_login(client, name, kwargs):
    """Request without login hits the login redirect"""
    path = reverse(name, kwargs=kwargs)
    response = client.get(path)
    LOG.debug(response)
    assert response.status_code == requests.codes['found']
    assert response.url == '/login/?next=' + path


def test_configs_view_no_configs(client):
    """If no configs in db, an appropriate message is shown."""
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:configs"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    configtree = response.context['roots']
    assert len(configtree) == 0  # 0 configs


def test_configs_view_config(client):
    """Create config and see that it is shown."""
    client.login(username='test', password='test')
    config = create_config("config #1")
    response = client.get(reverse("ec2spotmanager:configs"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    configtree = response.context['roots']
    assert len(configtree) == 1  # 1 config
    assert set(configtree) == {config}  # same config
    assert len(configtree[0].children) == 0
    assert_contains(response, "config #1")


def test_configs_view_configs(client):
    """Create configs and see that they are shown."""
    client.login(username='test', password='test')
    configs = (create_config("config #1"),
               create_config("config #2"))
    response = client.get(reverse("ec2spotmanager:configs"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    configtree = response.context['roots']
    assert len(configtree) == 2  # 2 configs
    assert set(configtree) == set(configs)  # same configs
    assert len(configtree[0].children) == 0
    assert len(configtree[1].children) == 0
    assert_contains(response, "config #1")
    assert_contains(response, "config #2")


def test_configs_view_config_tree(client):
    """Create nested configs and see that they are shown."""
    client.login(username='test', password='test')
    config1 = create_config("config #1")
    config2 = create_config("config #2", parent=config1)
    config3 = create_config("config #3")
    response = client.get(reverse("ec2spotmanager:configs"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    configtree = response.context['roots']
    assert len(configtree) == 2  # 2 top-level configs
    assert set(configtree), {config1 == config3}
    seen1 = seen3 = False
    for cfg in configtree:
        if cfg == config1:
            assert not seen1
            seen1 = True
            assert len(cfg.children) == 1
            assert set(cfg.children) == {config2}
        elif cfg == config3:
            assert not seen3
            seen3 = True
            assert len(cfg.children) == 0
        else:
            raise Exception("unexpected configuration: %s" % cfg.name)
    assert seen1
    assert seen3
    assert_contains(response, "config #1")
    assert_contains(response, "config #2")
    assert_contains(response, "config #3")


def test_create_config_view_create_form(client):
    """Config creation form should be shown"""
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:configcreate"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, "Create Configuration")
    assert_contains(response, 'name="name"')
    assert_contains(response, 'name="size"')
    assert_contains(response, 'name="cycle_interval"')


def test_create_config_view_create(client):
    """Config created via form should be added to db"""
    client.login(username='test', password='test')
    response = client.post(reverse("ec2spotmanager:configcreate"),
                           {'parent': '-1',
                            'name': 'config #1',
                            'size': '1',
                            'cycle_interval': '1',  # activate tsmith mode
                            'ec2_key_name': 'key #1',
                            'ec2_security_groups': 'group #1',
                            'ec2_instance_types': 'machine #1',
                            'ec2_image_name': 'ami #1',
                            'ec2_userdata': 'lorem ipsum',
                            'ec2_userdata_macros': 'yup=123,nope=456',
                            'ec2_allowed_regions': 'nowhere',
                            'max_price': '0.01',
                            'instance_tags': 'good=true, bad=false',
                            'ec2_raw_config': 'hello=world',
                            'gce_machine_types': 'machine #2',
                            'gce_image_name': 'cos #1',
                            'gce_container_name': 'alpine:latest',
                            'gce_disk_size': '12',
                            'gce_env': 'tag1=value1,tag2=value2',
                            'gce_cmd': 'cat',
                            'gce_args': 'foo,bar',
                            'gce_raw_config': 'tag3=value3,tag4=value4'})
    LOG.debug(response)
    cfg = PoolConfiguration.objects.get(name='config #1')
    assert cfg.parent is None
    assert cfg.size == 1
    assert cfg.cycle_interval == 1

    assert cfg.ec2_key_name == 'key #1'
    assert json.loads(cfg.ec2_security_groups) == ['group #1']
    assert json.loads(cfg.ec2_instance_types) == ['machine #1']
    assert cfg.ec2_image_name == 'ami #1'
    assert cfg.ec2_userdata_file.read() == b'lorem ipsum'
    assert json.loads(cfg.ec2_userdata_macros) == {'yup': '123', 'nope': '456'}
    assert json.loads(cfg.ec2_allowed_regions) == ['nowhere']
    assert cfg.max_price == decimal.Decimal('0.01')
    assert json.loads(cfg.instance_tags) == {'good': 'true', 'bad': 'false'}
    assert json.loads(cfg.ec2_raw_config) == {'hello': 'world'}
    assert json.loads(cfg.gce_machine_types) == ['machine #2']
    assert cfg.gce_image_name == 'cos #1'
    assert cfg.gce_container_name == 'alpine:latest'
    assert cfg.gce_disk_size == 12
    assert json.loads(cfg.gce_env) == {'tag1': 'value1', 'tag2': 'value2'}
    assert response.status_code == requests.codes['found']
    assert response.url == reverse('ec2spotmanager:configview', kwargs={'configid': cfg.pk})
    assert json.loads(cfg.gce_cmd) == ['cat']
    assert json.loads(cfg.gce_args) == ['foo', 'bar']
    assert json.loads(cfg.gce_raw_config) == {'tag3': 'value3', 'tag4': 'value4'}


def test_create_config_view_clone(client):
    """Creation form should contain source data"""
    client.login(username='test', password='test')
    cfg = create_config(name='config #1',
                        size=1234567,
                        cycle_interval=7654321,
                        ec2_key_name='key #1',
                        ec2_security_groups=['group #1'],
                        ec2_instance_types=['machine #1'],
                        ec2_image_name='ami #1',
                        ec2_userdata_macros={'yup': '123', 'nope': '456'},
                        ec2_allowed_regions=['nowhere'],
                        max_price='0.01',
                        instance_tags={'good': 'true', 'bad': 'false'},
                        ec2_raw_config={'hello': 'world'})
    response = client.get(reverse("ec2spotmanager:configcreate"), {'clone': cfg.pk})
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, "Clone Configuration")
    assert_contains(response, 'config #1 (Cloned)')
    assert_contains(response, '1234567')
    assert_contains(response, '7654321')
    assert_contains(response, 'key #1')
    assert_contains(response, 'group #1')
    assert_contains(response, 'machine #1')
    assert_contains(response, 'ami #1')
    assert_contains(response, 'yup=123')
    assert_contains(response, 'nope=456')
    assert_contains(response, 'nowhere')
    assert_contains(response, '0.01')
    assert_contains(response, 'bad=false')
    assert_contains(response, 'good=true')
    assert_contains(response, 'hello=world')


def test_view_config_view(client):
    """Create a config and view it"""
    cfg = create_config(name='config #1',
                        size=1234567,
                        cycle_interval=7654321,
                        ec2_key_name='key #1',
                        ec2_security_groups=['group #1'],
                        ec2_instance_types=['machine #1'],
                        ec2_image_name='ami #1',
                        ec2_userdata_macros={'yup': '123', 'nope': '456'},
                        ec2_allowed_regions=['nowhere'],
                        max_price='0.01',
                        instance_tags={'good': 'true', 'bad': 'false'},
                        ec2_raw_config={'hello': 'world'})
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:configview", kwargs={'configid': cfg.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, 'config #1')
    assert_contains(response, '1234567')
    assert_contains(response, '7654321')
    assert_contains(response, 'key #1')
    assert_contains(response, 'group #1')
    assert_contains(response, 'machine #1')
    assert_contains(response, 'ami #1')
    assert_contains(response, 'yup=123')
    assert_contains(response, 'nope=456')
    assert_contains(response, 'nowhere')
    assert_contains(response, '0.01')
    assert_contains(response, 'bad=false')
    assert_contains(response, 'good=true')
    assert_contains(response, 'hello=world')


def test_edit_config_view(client):
    """Edit an existing config"""
    cfg = create_config(name='config #1',
                        size=1234567,
                        cycle_interval=7654321,
                        ec2_key_name='key #1',
                        ec2_security_groups=['group #1'],
                        ec2_instance_types=['machine #1'],
                        ec2_image_name='ami #1',
                        ec2_userdata_macros={'yup': '123', 'nope': '456'},
                        ec2_allowed_regions=['nowhere'],
                        max_price='0.01',
                        instance_tags={'good': 'true', 'bad': 'false'},
                        ec2_raw_config={'hello': 'world'})
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:configedit", kwargs={'configid': cfg.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, "Edit Configuration")
    assert_contains(response, 'config #1')
    assert_contains(response, '1234567')
    assert_contains(response, '7654321')
    assert_contains(response, 'key #1')
    assert_contains(response, 'group #1')
    assert_contains(response, 'machine #1')
    assert_contains(response, 'ami #1')
    assert_contains(response, 'yup=123')
    assert_contains(response, 'nope=456')
    assert_contains(response, 'nowhere')
    assert_contains(response, '0.01')
    assert_contains(response, 'bad=false')
    assert_contains(response, 'good=true')
    assert_contains(response, 'hello=world')


def test_del_config_view_delete(client):
    """Delete an existing config"""
    cfg = create_config(name='config #1')
    client.login(username='test', password='test')
    response = client.post(reverse("ec2spotmanager:configdel", kwargs={'configid': cfg.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['found']
    assert response.url == reverse('ec2spotmanager:configs')
    assert PoolConfiguration.objects.count() == 0


def test_del_config_view_simple_get(client):
    """No errors are thrown in template"""
    cfg = create_config(name='config #1')
    client.login(username='test', password='test')
    response = client.get(reverse("ec2spotmanager:configdel", kwargs={'configid': cfg.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
