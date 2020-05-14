import datetime
import logging
import re
import botocore
import boto3
import boto.ec2
import boto.exception
from django.utils import timezone
from django.conf import settings
from laniakea.core.providers.ec2 import EC2Manager
from .CloudProvider import (CloudProvider, CloudProviderTemporaryFailure, CloudProviderInstanceCountError,
                            INSTANCE_STATE, INSTANCE_STATE_CODE, wrap_provider_errors)
from ..tasks import SPOTMGR_TAG
from ..common.ec2 import CORES_PER_INSTANCE


class EC2SpotCloudProvider(CloudProvider):
    def __init__(self):
        self.logger = logging.getLogger("ec2spotmanager")
        self.cluster = None
        self.connected_region = None

    def _connect(self, region):
        if self.connected_region != region:
            self.cluster = EC2Manager(None)  # create a new Manager to invalidate cached image names, etc.
            self.cluster.connect(region=region, aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                                 aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)
            self.connected_region = region
        return self.cluster

    @wrap_provider_errors
    def terminate_instances(self, instances_ids_by_region):
        for region, instance_ids in instances_ids_by_region.items():
            cluster = self._connect(region)
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
    def cancel_requests(self, requested_instances_by_region):
        for region, instance_ids in requested_instances_by_region.items():
            cluster = self._connect(region)
            cluster.cancel_spot_requests(instance_ids)

        self.logger.info("Canceling %s requests in region %s", len(instance_ids), region)

    @wrap_provider_errors
    def start_instances(self, config, region, zone, userdata, image, instance_type, count, _tags):
        images = self._create_laniakea_images(config)

        self.logger.info("Using instance type %s in region %s with availability zone %s.",
                         instance_type, region, zone)
        images["default"]['user_data'] = userdata.encode("utf-8")
        images["default"]['placement'] = zone
        images["default"]['count'] = count
        images["default"]['instance_type'] = instance_type

        cluster = self._connect(region)

        images['default']['image_id'] = image
        images['default'].pop('image_name')
        cluster.images = images

        try:
            instances = []
            self.logger.info("Creating %dx %s instances... (%d cores total)", count,
                             instance_type, count * CORES_PER_INSTANCE[instance_type])
            for ec2_request in cluster.create_spot_requests(config.max_price *
                                                            CORES_PER_INSTANCE[instance_type],
                                                            delete_on_termination=True,
                                                            timeout=10 * 60):
                instances.append(ec2_request)

            return {instance: {'status_code': INSTANCE_STATE["requested"],
                               'instance_id': instance,
                               'hostname': ''}
                    for instance in instances}

        except (boto.exception.EC2ResponseError, boto.exception.BotoServerError) as msg:
            code_match = re.search(r"<Code>([A-Za-z]+)</Code>", str(msg))
            if code_match is not None:
                code = code_match.group(1)
                if code == "MaxSpotInstanceCountExceeded":
                    self.logger.warning("start_instances: Maximum instance count exceeded for region %s",
                                        region)
                    raise CloudProviderInstanceCountError(
                        "Auto-selected region exceeded its maximum spot instance count.")
                if code == "RequestLimitExceeded":
                    self.logger.warning("Request limit exceeded for region %s, trying again later.", region)
                    raise CloudProviderTemporaryFailure("Request limit exceeded for region %s" % (region,))
                if code in {"InternalError", "Unavailable"}:
                    raise CloudProviderTemporaryFailure("start_instances in region %s: %s" % (region, msg))
            raise

    @wrap_provider_errors
    def check_instances_requests(self, region, instances, tags):
        successful_requests = {}
        failed_requests = {}

        cluster = self._connect(region)
        try:
            results = cluster.check_spot_requests(instances, tags)
        except boto.exception.BotoServerError as msg:
            if "RequestLimitExceeded" in str(msg):
                self.logger.warning("Request limit exceeded for region %s, trying again later.", region)
                raise CloudProviderTemporaryFailure("Request limit exceeded for region %s" % (region,))
            else:
                raise

        for req_id, result in zip(instances, results):
            if isinstance(result, boto.ec2.instance.Instance):
                # state_code is a 16-bit value where the high byte is
                # an opaque internal value and should be ignored.
                status_code = result.state_code & 255
                status_desc = INSTANCE_STATE_CODE.get(status_code, "Unknown(%d)" % (status_code,))

                self.logger.info("Spot request fulfilled %s -> %s (status: %s)", req_id, result.id, status_desc)

                # spot request has been fulfilled
                successful_requests[req_id] = {}
                successful_requests[req_id]['hostname'] = result.public_dns_name
                successful_requests[req_id]['instance_id'] = result.id
                successful_requests[req_id]['status_code'] = status_code
                # Now that we saved the object into our database, mark the instance as updatable
                # so our update code can pick it up and update it accordingly when it changes states
                result.add_tag(SPOTMGR_TAG + "-Updatable", "1")

            # request object is returned in case request is closed/cancelled/failed
            elif isinstance(result, boto.ec2.spotinstancerequest.SpotInstanceRequest):
                if result.state in {"cancelled", "closed"}:
                    # request was not fulfilled for some reason.. blacklist this type/zone for a while
                    # XXX: in some cases we are the ones who cancelled the request, if so we should not blacklist
                    self.logger.info("Request %s is %s and %s", req_id, result.status.code, result.state)
                    failed_requests[req_id] = {}
                    failed_requests[req_id]['action'] = 'blacklist'
                    failed_requests[req_id]['instance_type'] = result.launch_specification.instance_type
                    failed_requests[req_id]['reason'] = \
                        'Spot request %s in %s is %s and %s' % (req_id, region, result.status.code, result.state)
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
        cluster = self._connect(region)

        try:
            if pool_id is None:
                boto_instances = cluster.find(filters={"tag-key": SPOTMGR_TAG + "-PoolId"})
            else:
                boto_instances = cluster.find(filters={"tag:" + SPOTMGR_TAG + "-PoolId": str(pool_id)})
        except boto.exception.BotoServerError as msg:
            code_match = re.search(r"<Code>([A-Za-z]+)</Code>", str(msg))
            if code_match is not None:
                code = code_match.group(1)
                if code == "Unavailable":
                    raise CloudProviderTemporaryFailure("getting instances in region %s: %s" % (region, msg))
            raise

        for instance in boto_instances:
            instance_states[instance.id] = {}
            instance_states[instance.id]['status'] = instance.state_code & 255
            instance_states[instance.id]['tags'] = instance.tags

        return instance_states

    @wrap_provider_errors
    def get_image(self, region, config):
        cluster = self._connect(region)
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
        return config.max_price

    @staticmethod
    def get_tags(config):
        return config.instance_tags

    @staticmethod
    def get_name():
        return 'EC2Spot'

    @staticmethod
    def config_supported(config):
        fields = ['ec2_allowed_regions', 'max_price', 'ec2_key_name', 'ec2_security_groups',
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
