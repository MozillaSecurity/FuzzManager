'''
Cloud Provider Interface

@author:     Raymond Forbes (:rforbes)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    truber@mozilla.com
'''

import functools
import logging
import socket
import ssl
import traceback
from abc import ABCMeta, abstractmethod

import six

INSTANCE_STATE_CODE = {-1: "requested", 0: "pending", 16: "running", 32: "shutting-down",
                       48: "terminated", 64: "stopping", 80: "stopped"}
INSTANCE_STATE = dict((val, key) for key, val in INSTANCE_STATE_CODE.items())

# List of currently supported providers. This and what is returned by get_name() must match
PROVIDERS = ['EC2Spot', 'GCE']


class CloudProviderError(Exception):
    TYPE = 'unclassified'

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return '%s: %s (%s)' % (type(self).__name__, self.message, self.TYPE)


class CloudProviderTemporaryFailure(CloudProviderError):
    TYPE = 'temporary-failure'


class CloudProviderInstanceCountError(CloudProviderError):
    TYPE = 'max-spot-instance-count-exceeded'


def wrap_provider_errors(wrapped):
    @functools.wraps(wrapped)
    def wrapper(*args, **kwds):
        try:
            return wrapped(*args, **kwds)
        except (ssl.SSLError, socket.error) as exc:
            logging.getLogger("ec2spotmanager").exception("")
            raise CloudProviderTemporaryFailure('%s: %s' % (wrapped.__name__, exc))
        except CloudProviderError:
            logging.getLogger("ec2spotmanager").exception("")
            raise
        except Exception:
            logging.getLogger("ec2spotmanager").exception("")
            raise CloudProviderError('%s: unhandled error: %s' % (wrapped.__name__, traceback.format_exc()))

    return wrapper


@six.add_metaclass(ABCMeta)
class CloudProvider():
    '''
    Abstract base class that defines what interfaces Cloud Providers must implement
    '''
    @abstractmethod
    def terminate_instances(self, instances_ids_by_region):
        '''
        Take a list of running instances and stop them in the cloud provider.

        @ptype instances_ids_by_region: dictionary
        @param instances_ids_by_region: keys are regions and values are instances.

        @rtype: none
        @return: none
        '''
        return

    @abstractmethod
    def cancel_requests(self, requested_instances_by_region):
        '''
        Cancel requests that have not become running instances.

        @ptype requested_instances_region: dictionary
        @param requested_instances_region: keys are regions and values are request ids.
        '''
        return

    @abstractmethod
    def start_instances(self, config, region, zone, userdata, image, instance_type, count, tags):
        '''
        Start instances using specified configuration.

        @ptype config: FlatObject
        @param config: flattened config. We use this for any cloud provider specific fields needed to create an instance

        @ptype region: string
        @param region: region where instances are to be started

        @ptype zone: string
        @param zone: zone the instances will be started in

        @ptype userdata: UserData object
        @param userdata: userdata script for instances

        @ptype image: string
        @param image: image reference used to start instances

        @ptype instance_type: string
        @param instance_type: type of instance

        @ptype count: int
        @param count: number of instances to start

        @ptype tags: dictionary
        @param tags: instance tags.

        @rtype: list
        @return: Request IDs given to us by the cloud provider. This can be the instance ID if the provider
                 does not use different IDs for instances and requests.
        '''
        return

    @abstractmethod
    def check_instances_requests(self, region, instances, tags):
        '''
        Take a list of requested instances and determines the state of each instance.
        Since this is the first point we see an actual running instance
        we set the tags on the instances here as well.

        We create a dictionary of succesful requests. This has hostname,
        instance id, and status of each instance. This status must match the
        INSTANCE_STATE in CloudProvider.

        Failed requests will have an action and instance type. Currently, we
        support actions of 'blacklist' and disable_pool.

        @ptype region: string
        @param region: the region the instances are in

        @ptype instances: list
        @param isntances: instance request IDs

        @ptype tags: dictionary
        @param tags: instance tags.

        @rtype: tuple
        @return: tuple containing 2 dicts: successful request IDs and failed request IDs.
        '''
        return

    @abstractmethod
    def check_instances_state(self, pool_id, region):
        '''
        Takes a pool ID, searches the cloud provider for instances in that pool (using the tag)
        and returns a dictionary of instances with their state as value.

        @ptype pool_id: int
        @param list of pool instances are located in. We search for
        instances using the poolID tag

        @ptype region: string
        @param region: region where instances are located

        @rtype: dictionary
        @return: running instances and their states. State must comply with INSTANCE_STATE defined in CloudProvider
        '''
        return

    @abstractmethod
    def get_image(self, region, config):
        '''
        Takes a configuration and returns a provider specific image name.

        @ptype region: string
        @param region: region

        @ptype config: FlatObject
        @param config: flattened config

        @rtype: string
        @return: cloud provider ID for image
        '''
        return

    @staticmethod
    @abstractmethod
    def get_cores_per_instance():
        '''
        returns dictionary of instance types and their number of cores

        @rtype: dictionary
        @return: instance types and how many cores per instance type
        '''
        return

    @staticmethod
    @abstractmethod
    def get_allowed_regions(config):
        '''
        Takes a configuration and returns cloud provider specific regions.

        @ptype config: FlatObject
        @param config: pulling regions from config

        @rtype: list
        @return: regions pulled from config
        '''
        return

    @staticmethod
    @abstractmethod
    def get_image_name(config):
        '''
        Takes a configuration and returns cloud provider specific image name.

        @ptype config: FlatObject
        @param config: pulling image name from config

        @rtype: string
        @return: cloud specific image name from config
        '''
        return

    @staticmethod
    @abstractmethod
    def get_instance_types(config):
        '''
        Takes a configuration and returns a list of cloud provider specific instance_types.

        @ptype config: FlatObject
        @param config: pulling instance types from config

        @rtype: list
        @return: list of cloud specific instance_types from config
        '''
        return

    @staticmethod
    @abstractmethod
    def get_max_price(config):
        '''
        Takes a configuration and returns the cloud provider specific max_price.

        @ptype config: FlatObject
        @param config: pulling max_price from config

        @rtype: float
        @return: cloud specific max_price
        '''
        return

    @staticmethod
    @abstractmethod
    def get_tags(config):
        '''
        Takes a configuration and returns a dictionary of cloud provider specific tags.

        @ptype config: FlatObject
        @param config: pulling tags field

        @rtype: dictionary
        @return: cloud specific tags field
        '''
        return

    @staticmethod
    @abstractmethod
    def get_name():
        '''
        used to return name of cloud provider

        @rtype: string
        @return: string representation of the cloud provider
        '''
        return

    @staticmethod
    @abstractmethod
    def config_supported(config):
        '''Compares the fields provided in the config with those required by the cloud
        provider. If any field is missing, return False.

        @ptype config: FlatObject
        @param config: Flattened config

        @rtype: bool
        @return: True if all required cloud specific fields in config
        '''
        return

    @abstractmethod
    def get_prices_per_region(self, region_name, instance_types):
        '''
        takes region and instance_types and returns a dictionary of prices
        prices are stored with keys like 'provider:price:{instance-type}'
        and values {region: {zone (if used): [price value, ...]}}

        @ptype region_name: string
        @param region_name: region to grab prices

        @ptype instance_types: list
        @param instance_types: list of instance_types

        @rtype: dictionary
        @return: dictionary of prices as specified above.
        '''
        return

    @staticmethod
    def get_instance(provider):
        '''
        This is a method that is used to instantiate the provider class.
        '''
        classname = provider + 'CloudProvider'
        providerModule = __import__('ec2spotmanager.CloudProvider.%s' % classname, fromlist=[classname])
        providerClass = getattr(providerModule, classname)
        return providerClass()
