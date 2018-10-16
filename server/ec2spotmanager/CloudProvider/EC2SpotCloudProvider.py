import datetime
import functools
import logging
import socket
import ssl
import botocore
import boto3
import boto.ec2
import boto.exception
from django.utils import timezone
from django.conf import settings
from laniakea.core.providers.ec2 import EC2Manager
from .CloudProvider import (CloudProvider, CloudProviderTemporaryFailure, CloudProviderInstanceCountError,
                            CloudProviderError, INSTANCE_STATE)
from ..tasks import SPOTMGR_TAG
from ..common.ec2 import CORES_PER_INSTANCE


def wrap_provider_errors(wrapped):
    @functools.wraps(wrapped)
    def wrapper(*args, **kwds):
        try:
            return wrapped(*args, **kwds)
        except (ssl.SSLError, socket.error) as exc:
            raise CloudProviderTemporaryFailure('%s: %s' % (wrapped.__name__, exc))
        except CloudProviderError:
            raise
        except Exception as exc:
            raise CloudProviderError('%s: unhandled error: %s' % (wrapped.__name__, exc))

    return wrapper


class EC2SpotCloudProvider(CloudProvider):
    def __init__(self):
        self.logger = logging.getLogger("ec2spotmanager")

    @wrap_provider_errors
    def terminate_instances(self, instances_ids_by_region):
        for region, instance_ids in instances_ids_by_region.items():
            cluster = EC2Manager(None)
            cluster.connect(region=region, aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

            self.logger.info("Terminating %s instances in region %s", len(instance_ids), region)
            boto_instances = cluster.find(instance_ids=instance_ids)
            # Data consistency checks
            for boto_instance in boto_instances:
                # state_code is a 16-bit value where the high byte is
                # an opaque internal value and should be ignored.
                state_code = boto_instance.state_code & 255
                if not ((boto_instance.id in instance_ids) or
                        (state_code == INSTANCE_STATE['shutting-down'] or
                         state_code == INSTANCE_STATE['terminated'])):
                    self.logger.error("Instance with EC2 ID %s (status %d) is not in region list for region %s",
                                      boto_instance.id, state_code, region)

                cluster.terminate(boto_instances)

    @wrap_provider_errors
    def start_instances(self, config, region, zone, userdata, image, instance_type, count=1):
        images = self._create_laniakea_images(config)

        self.logger.info("Using instance type %s in region %s with availability zone %s.",
                         instance_type, region, zone)
        images["default"]['user_data'] = userdata.encode("utf-8")
        images["default"]['placement'] = zone
        images["default"]['count'] = count
        images["default"]['instance_type'] = instance_type

        cluster = EC2Manager(None)
        cluster.connect(region=region, aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

        images['default']['image_id'] = image
        images['default'].pop('image_name')
        cluster.images = images

        try:
            instances = []
            self.logger.info("Creating %dx %s instances... (%d cores total)", count,
                             instance_type, count * CORES_PER_INSTANCE[instance_type])
            for ec2_request in cluster.create_spot_requests(config.ec2_max_price *
                                                            CORES_PER_INSTANCE[instance_type],
                                                            delete_on_termination=True,
                                                            timeout=10 * 60):
                instances.append(ec2_request)

            return instances

        except (boto.exception.EC2ResponseError, boto.exception.BotoServerError) as msg:
            if "MaxSpotInstanceCountExceeded" in str(msg):
                self.logger.warning("start_instances: Maximum instance count exceeded for region %s",
                                    region)
                raise CloudProviderInstanceCountError(
                    "Auto-selected region exceeded its maximum spot instance count.")
            elif "Service Unavailable" in str(msg):
                raise CloudProviderTemporaryFailure("start_instances in region %s: %s" % (region, msg))
            raise

    @wrap_provider_errors
    def check_instances_requests(self, region, instances, tags):
        successful_requests = {}
        failed_requests = {}

        cluster = EC2Manager(None)
        cluster.connect(region=region, aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

        results = cluster.check_spot_requests(instances, tags)

        for req_id, result in zip(instances, results):
            if isinstance(result, boto.ec2.instance.Instance):
                self.logger.info("Spot request fulfilled %s -> %s", req_id, result.id)

                # spot request has been fulfilled
                successful_requests[req_id] = {}
                successful_requests[req_id]['hostname'] = result.public_dns_name
                successful_requests[req_id]['instance_id'] = result.id
                # state_code is a 16-bit value where the high byte is
                # an opaque internal value and should be ignored.
                successful_requests[req_id]['status_code'] = result.state_code & 255
                # Now that we saved the object into our database, mark the instance as updatable
                # so our update code can pick it up and update it accordingly when it changes states
                result.add_tag(SPOTMGR_TAG + "-Updatable", "1")

            # request object is returned in case request is closed/cancelled/failed
            elif isinstance(result, boto.ec2.spotinstancerequest.SpotInstanceRequest):
                if result.state in {"cancelled", "closed"}:
                    # request was not fulfilled for some reason.. blacklist this type/zone for a while
                    self.logger.info("Spot request %s is %s", req_id, result.state)
                    failed_requests[req_id] = {}
                    failed_requests[req_id]['action'] = 'blacklist'
                    failed_requests[req_id]['instance_type'] = result.launch_specification.instance_type
                elif result.state in {"open", "active"}:
                    # this should not happen! warn and leave in DB in case it's fulfilled later
                    self.logger.warning("Request %s is %s and %s.",
                                        req_id,
                                        result.status.code,
                                        result.state)
                else:  # state=failed
                    self.logger.error("Request %s is %s and %s." % (req_id, result.status.code, result.state))
                    failed_requests[req_id] = {}
                    failed_requests[req_id]['action'] = 'disable_pool'
                    break
            elif result is None:
                self.logger.info("spot request %s is still open", req_id)
            else:
                self.logger.warning("Spot request %s returned %s", req_id, type(result).__name__)

        return (successful_requests, failed_requests)

    @wrap_provider_errors
    def check_instances_state(self, pool_id, region):

        instance_states = {}
        cluster = EC2Manager(None)
        cluster.connect(region=region, aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

        boto_instances = cluster.find(filters={"tag:" + SPOTMGR_TAG + "-PoolId": str(pool_id)})

        for instance in boto_instances:
            if instance.state_code not in [INSTANCE_STATE['shutting-down'], INSTANCE_STATE['terminated']]:
                instance_states[instance.id] = {}
                instance_states[instance.id]['status'] = instance.state_code & 255
                instance_states[instance.id]['tags'] = instance.tags

        return instance_states

    @wrap_provider_errors
    def get_image(self, region, config):
        cluster = EC2Manager(None)
        cluster.connect(region=region, aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        ami = cluster.resolve_image_name(config.ec2_image_name)
        return ami

    @staticmethod
    def get_cores_per_instance():
        return CORES_PER_INSTANCE

    @staticmethod
    def get_allowed_regions(config):
        return config.ec2_allowed_regions

    @staticmethod
    def get_image_name(config):
        return config.ec2_image_name

    @staticmethod
    def get_instance_types(config):
        return config.ec2_instance_types

    @staticmethod
    def get_max_price(config):
        return config.ec2_max_price

    @staticmethod
    def get_tags(config):
        return config.ec2_tags

    @staticmethod
    def get_name():
        return 'EC2Spot'

    @staticmethod
    def config_supported(config):
        fields = ['ec2_allowed_regions', 'ec2_max_price', 'ec2_key_name', 'ec2_security_groups',
                  'ec2_instance_types', 'ec2_image_name']
        return all(config.get(key) for key in fields)

    @wrap_provider_errors
    def get_prices_per_region(self, region_name, instance_types=None):
        '''Gets spot prices of the specified region and instance type'''
        prices = {}  # {instance-type: region: {az: [prices]}}}
        zone_blacklist = ["us-east-1a", "us-east-1f"]

        now = timezone.now()

        # TODO: Make configurable
        spot_history_args = {
            'Filters': [{'Name': 'product-description', 'Values': ['Linux/UNIX']}],
            'StartTime': now - datetime.timedelta(hours=6)
        }
        if instance_types is not None:
            spot_history_args['InstanceTypes'] = instance_types

        cli = boto3.client('ec2', region_name=region_name, aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                           aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
        paginator = cli.get_paginator('describe_spot_price_history')
        try:
            for result in paginator.paginate(**spot_history_args):
                for price in result['SpotPriceHistory']:
                    if price['AvailabilityZone'] in zone_blacklist:
                        continue
                    (prices
                     .setdefault(price['InstanceType'], {})
                     .setdefault(region_name, {})
                     .setdefault(price['AvailabilityZone'], [])
                     .append(float(price['SpotPrice'])))
        except botocore.exceptions.EndpointConnectionError as exc:
            raise RuntimeError("Boto connection error: %s" % (exc,))

        return prices

    @staticmethod
    def _create_laniakea_images(config):
        images = {"default": {}}

        # These are the configuration keys we want to put into the target configuration
        # without further preprocessing, except for the adjustment of the key name itself.
        keys = [
            'ec2_key_name',
            'ec2_image_name',
            'ec2_security_groups',
        ]

        for key in keys:
            lkey = key.replace("ec2_", "", 1)
            images["default"][lkey] = config[key]

        if config.ec2_raw_config:
            images["default"].update(config.ec2_raw_config)

        return images
