'''
GCE Cloud Provider

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    truber@mozilla.com
'''
import logging
import requests
import time
import yaml
from django.conf import settings
from laniakea.core.providers.gce import ComputeEngineManager, ComputeEngineManagerException
from .CloudProvider import (CloudProvider, CloudProviderTemporaryFailure, INSTANCE_STATE,
                            INSTANCE_STATE_CODE, wrap_provider_errors)
from ..tasks import SPOTMGR_TAG
from ..common.gce import CORES_PER_INSTANCE, RAM_PER_INSTANCE


#
# Google Compute Platform provider for EC2SpotManager
#
# Currently laniakea is using libcloud as the backend, which means operations are synchronous.
# API access is not very optimal as a result. Launching typically takes ~30s and terminating ~80s.
#


class _LowercaseDict(dict):

    def __init__(self, *args, **kwds):
        super(_LowercaseDict, self).__init__()
        if len(args) > 1:
            raise TypeError("dict expected at most 1 arguments, got %d" % (len(args),))
        if args:
            if hasattr(args[0], "items"):
                for (k, v) in args[0].items():
                    self[k] = v
            else:
                for (k, v) in args[0]:
                    self[k] = v
        elif kwds:
            for (k, v) in kwds.items():
                self[k] = v

    def __getitem__(self, key):
        return super(_LowercaseDict, self).__getitem__(key.lower())

    def __setitem__(self, key, value):
        return super(_LowercaseDict, self).__setitem__(key.lower(), value.lower())

    def __delitem__(self, key):
        return super(_LowercaseDict, self).__delitem__(key.lower())

    def __contains__(self, item):
        return super(_LowercaseDict, self).__contains__(item.lower())


class GCECloudProvider(CloudProvider):
    '''Implementation of CloudProvider interface for GCE.
    '''
    NODE_STATE_MAP = {
        "PROVISIONING": INSTANCE_STATE["requested"],
        "STAGING": INSTANCE_STATE["pending"],
        "RUNNING": INSTANCE_STATE["running"],
        "STOPPING": INSTANCE_STATE["stopping"],
        "TERMINATED": INSTANCE_STATE["terminated"],
        "UNKNOWN": INSTANCE_STATE["pending"],
    }

    def __init__(self):
        self.logger = logging.getLogger("ec2spotmanager.gce")
        self.cluster = None

    def _connect(self):
        if self.cluster is None:
            self.cluster = ComputeEngineManager(settings.GCE_CLIENT_EMAIL,
                                                settings.GCE_PRIVATE_KEY,
                                                settings.GCE_PROJECT_ID)
            retries = [1, 5, 10, 30, None]
            for retry in retries:
                try:
                    self.cluster.connect(credential_file=settings.GCE_AUTH_CACHE)
                    break
                except ComputeEngineManagerException as error:
                    if retry is None:
                        raise
                    self.logger.warning("Connect error: %s, retrying in %d seconds", error, retry)
                    time.sleep(retry)

        return self.cluster

    @wrap_provider_errors
    def terminate_instances(self, instances_ids_by_region):
        for region, instance_ids in instances_ids_by_region.items():
            assert region == "global", "Invalid region name for GCE: %s (only 'global' supported)" % (region,)
            cluster = self._connect()
            self.logger.info("Terminating %s instances in GCE", len(instance_ids))
            nodes = cluster.filter().name(instance_ids).nodes
            # Data consistency checks
            for node in nodes:
                if not (node.name in instance_ids or node.state == "STOPPED"):
                    self.logger.error("Instance with GCE Name %s (status %s) is not in node list",
                                      node.name, node.state)

            cluster.terminate_nowait(nodes)

    @wrap_provider_errors
    def cancel_requests(self, requested_instances_by_region):
        # no difference in how pending nodes are terminated in GCE
        self.logger.info("Canceling %d requests in GCE", len(requested_instances_by_region))
        self.terminate_instances(requested_instances_by_region)

    def _node_to_instance(self, node):
        instance = {}
        ip_addr = node.public_ips[0]
        instance['hostname'] = ".".join(reversed(ip_addr.split("."))) + ".bc.googleusercontent.com"
        instance['instance_id'] = node.name
        instance['status_code'] = self.NODE_STATE_MAP[node.extra['status']]
        return instance

    @wrap_provider_errors
    def start_instances(self, config, region, zone, _userdata, image, instance_type, count, tags):
        assert region == "global", "Invalid region name for GCE: %s (only 'global' supported)" % (region,)
        self.logger.info("Using machine type %s in GCE availability zone %s.", instance_type, zone)
        cluster = self._connect()
        container_spec = {
            "spec": {
                "containers": [
                    {
                        "name": "fuzz",
                        "image": config.gce_container_name,
                        "stdin": False,
                        "tty": False,
                        "volumeMounts": [
                            {
                                "name": "host-path-0",
                                "mountPath": "/dev/shm",
                                "readOnly": False,
                            },
                        ],
                    },
                ],
                "restartPolicy": "Always",
                "volumes": [
                    {
                        "name": "host-path-0",
                        "hostPath": {
                            "path": "/dev/shm",
                        },
                    },
                ],
            },
        }
        container_spec["spec"]["containers"][0]["securityContext"] = {"capabilities": {"add": "SYS_PTRACE"}}
        if config.gce_docker_privileged:
            container_spec["spec"]["containers"][0]["securityContext"]["privileged"] = True
        if config.gce_cmd:
            container_spec["spec"]["containers"][0]["command"] = config.gce_cmd
        if config.gce_args:
            container_spec["spec"]["containers"][0]["args"] = config.gce_args
        if config.gce_env:
            container_spec["spec"]["containers"][0]["env"] = \
                [{"name": name, "value": value} for name, value in config.gce_env.items()]

        disk = cluster.build_bootdisk(image, config.gce_disk_size, True)
        conf = cluster.build_container_vm(yaml.safe_dump(container_spec), disk, zone=zone, preemptible=True)
        tags = _LowercaseDict(tags)
        tags[SPOTMGR_TAG + "-Updatable"] = "1"
        conf["ex_labels"] = tags
        self.logger.info("Creating %dx %s instances... (%d cores total)", count,
                         instance_type, count * CORES_PER_INSTANCE[instance_type])
        nodes = cluster.create(instance_type, count, conf, image=image)
        return {node.name: self._node_to_instance(node) for node in nodes}

    @wrap_provider_errors
    def check_instances_requests(self, region, instances, tags):
        # this isn't a spot provider, and tags were already set at instance creation
        assert region == "global", "Invalid region name for GCE: %s (only 'global' supported)" % (region,)
        cluster = self._connect()

        requests = {}

        libcloud_nodes = cluster.filter().name(names=instances).nodes

        for node in libcloud_nodes:
            requests[node.name] = self._node_to_instance(node)
            self.logger.info("Instance %s (%s) is %s (%s)", node.name, requests[node.name]['hostname'],
                             node.extra['status'], INSTANCE_STATE_CODE[requests[node.name]['status_code']])
            # Now that we saved the object into our database, mark the instance as updatable
            # so our update code can pick it up and update it accordingly when it changes states
            # TODO: This should use a laniakea API if issue laniakea issue #40 is fixed. (if it isn't removed)
            tags = _LowercaseDict(tags)
            tags[SPOTMGR_TAG + "-Updatable"] = "1"
            cluster.gce.ex_set_node_labels(node, tags)

        return (requests, {})

    @wrap_provider_errors
    def check_instances_state(self, pool_id, region):
        # TODO: if we could return a hostname, `check_instances_requests` would be unnecessary for this provider
        assert region == "global", "Invalid region name for GCE: %s (only 'global' supported)" % (region,)

        instance_states = {}
        cluster = self._connect()

        try:
            if pool_id is None:
                libcloud_nodes = cluster.filter().has_labels([(SPOTMGR_TAG + "-PoolId").lower()]).nodes
            else:
                libcloud_nodes = cluster.filter().labels({(SPOTMGR_TAG + "-PoolId").lower(): str(pool_id)}).nodes
        except Exception as exc:
            if "Please try again" in str(exc):
                raise CloudProviderTemporaryFailure(str(exc))
            raise

        for node in libcloud_nodes:

            instance_states[node.name] = {}
            instance_states[node.name]['status'] = self.NODE_STATE_MAP[node.extra['status']]
            instance_states[node.name]['tags'] = _LowercaseDict(node.extra['labels'])

        return instance_states

    def get_image(self, region, config):
        assert region == "global", "Invalid region name for GCE: %s (only 'global' supported)" % (region,)
        return config.gce_image_name

    @staticmethod
    def get_cores_per_instance():
        return CORES_PER_INSTANCE

    @staticmethod
    def get_allowed_regions(_config):
        return ["global"]

    @staticmethod
    def get_image_name(config):
        return config.gce_image_name

    @staticmethod
    def get_instance_types(config):
        return config.gce_machine_types

    @staticmethod
    def get_max_price(config):
        return config.max_price

    @staticmethod
    def get_tags(config):
        return config.instance_tags

    @staticmethod
    def get_name():
        return 'GCE'

    @staticmethod
    def config_supported(config):
        fields = ['gce_machine_types', 'max_price', 'gce_image_name', 'gce_container_name',
                  'gce_disk_size']
        return all(config.get(key) for key in fields)

    def get_prices_per_region(self, region_name, instance_types=None):
        # Pricing information is not perfect. The API Zones don't map to the data provided by Cloud Billing
        # API. We usually get one price per zone (eg. us-east1), so we just assume that -a, -b, and -c have
        # the same price. In some cases we do get details like "price in Tokyo" and "price in Japan"
        # (both asia-northeast1), but we don't know which sub-zone those are, so we take the worst price and
        # apply it to the whole zone to be conservative.
        assert region_name == "global"

        def get_price(sku):
            assert len(sku["pricingInfo"]) == 1
            expr = sku["pricingInfo"][0]["pricingExpression"]
            assert len(expr["tieredRates"]) == 1, expr["tieredRates"]
            rate = expr["tieredRates"][0]
            unit = int(rate["unitPrice"]["units"])
            nanos = rate["unitPrice"]["nanos"]
            return ((unit + float(nanos) / 1e9), expr["usageUnit"])

        zones = {}
        service_id = "6F81-5844-456A"  # Compute Engine
        compute_skus_url = "https://cloudbilling.googleapis.com/v1/services/" + service_id + "/skus"

        def _get_skus_paginated():
            params = {"key": settings.GCE_API_KEY}
            data = requests.get(compute_skus_url, params=params).json()
            while True:
                for sku in data["skus"]:
                    yield sku
                if data["nextPageToken"]:
                    params["pageToken"] = data["nextPageToken"]
                    data = requests.get(compute_skus_url, params=params).json()
                else:
                    break

        for sku in _get_skus_paginated():
            if sku["category"]["resourceFamily"] == "Compute" and \
                    sku["category"]["usageType"] == "Preemptible":

                # group by sku["serviceRegions"] and sku["category"]["resourceGroup"]
                price, unit = get_price(sku)

                # I don't know what this is for, so make sure it's 0
                if sku["description"].startswith("CPU Upgrade Premium"):
                    assert price == 0, (
                        "CPU Upgrade Premium is not 0 in %r/%r, please update pricing function"
                        % (sku["serviceRegions"], sku["category"])
                    )
                    continue

                # these are the resourceGroup/descriptions we care about:
                #  CPU/Preemptible Memory-optimized Instance Core -> memopt-cpu
                #  F1Micro/Preemptible Micro Instance with burstable CPU -> f1-inst
                #  G1Small/Preemptible Small Instance with 1 VCPU -> g1-inst
                #  N1Standard/Preemptible N1 Predefined Instance Ram -> n1-ram
                #  N1Standard/Preemptible N1 Predefined Instance Core -> n1-cpu
                #  RAM/Preemptible Memory-optimized Instance Ram -> memopt-ram
                what = None
                if sku["category"]["resourceGroup"] == "CPU":
                    if sku["description"].startswith("Preemptible Memory-optimized Instance Core"):
                        what = "memopt-cpu"
                elif sku["category"]["resourceGroup"] == "F1Micro":
                    if sku["description"].startswith("Preemptible Micro Instance with burstable CPU"):
                        what = "f1-inst"
                elif sku["category"]["resourceGroup"] == "G1Small":
                    if sku["description"].startswith("Preemptible Small Instance with 1 VCPU"):
                        what = "g1-inst"
                elif sku["category"]["resourceGroup"] == "N1Standard":
                    if sku["description"].startswith("Preemptible N1 Predefined Instance Ram"):
                        what = "n1-ram"
                    elif sku["description"].startswith("Preemptible N1 Predefined Instance Core"):
                        what = "n1-cpu"
                elif sku["category"]["resourceGroup"] == "RAM":
                    if sku["description"].startswith("Preemptible Memory-optimized Instance Ram"):
                        what = "memopt-ram"
                if what is None:
                    continue

                if what.endswith("-cpu") or what.endswith("-inst"):
                    assert unit == "h"
                else:
                    assert what.endswith("-ram")
                    assert unit == "GiBy.h"

                for region in sku["serviceRegions"]:
                    zonedata = zones.setdefault(region, {})
                    # TODO: the friendly description describes the zone, but I have no way of mapping
                    #       that to an API zone (eg. Tokyo & Japan -> asia-northeast1-a & asia-northeast1-b
                    zonedata.setdefault(what, []).append(price)

        # now we have all the data, and just have to calculate for our instance types and return
        result = {}  # {instance-type: {region: {az: [prices]}}}
        for instance_type, cores in CORES_PER_INSTANCE.items():
            mem = RAM_PER_INSTANCE[instance_type]

            keys = {}
            if instance_type.startswith("n1-ultramem-") or instance_type.startswith("n1-megamem-"):
                keys["mem"] = "memopt-ram"
                keys["cpu"] = "memopt-cpu"
            elif instance_type.startswith("n1-"):
                keys["mem"] = "n1-ram"
                keys["cpu"] = "n1-cpu"
            elif instance_type == "f1-micro":
                keys["instance"] = "f1-inst"
            else:
                assert instance_type == "g1-small", "instance type is %s" % (instance_type,)
                keys["instance"] = "g1-inst"

            for zone, prices in zones.items():
                if any(key not in prices for key in keys.values()):
                    continue
                region = result.setdefault(instance_type, {region_name: {}})[region_name]
                assert zone not in region
                region[zone] = [max(prices.get(keys.get("cpu"), [0])) * cores +
                                max(prices.get(keys.get("mem"), [0])) * mem +
                                max(prices.get(keys.get("instance"), [0]))]

        # since we can't distinguish between zones using the billing API (see TODO above)
        # return the pricing data for all zones within the GCE region
        all_zones_result = {}
        for instance_type, all_regions in result.items():
            for region, region_data in all_regions.items():
                all_zones_result[instance_type] = {}
                all_zones_region = all_zones_result[instance_type].setdefault(region, {})
                for zone, prices in region_data.items():
                    all_zones_region[zone + "-a"] = prices
                    all_zones_region[zone + "-b"] = prices
                    all_zones_region[zone + "-c"] = prices

        return all_zones_result
