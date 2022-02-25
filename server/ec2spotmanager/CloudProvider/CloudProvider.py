"""
Cloud Provider Interface

@author:     Raymond Forbes (:rforbes)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    truber@mozilla.com
"""

from __future__ import annotations

import functools
import logging
import ssl
import traceback
from abc import ABCMeta, abstractmethod
from decimal import Decimal
from typing import Any, Callable, TypeVar

from ec2spotmanager.models import PoolConfiguration

INSTANCE_STATE_CODE = {
    -1: "requested",
    0: "pending",
    16: "running",
    32: "shutting-down",
    48: "terminated",
    64: "stopping",
    80: "stopped",
}
INSTANCE_STATE = {val: key for key, val in INSTANCE_STATE_CODE.items()}

# List of currently supported providers. This and what is returned by get_name() must
# match
PROVIDERS = ["EC2Spot", "GCE"]
RetType = TypeVar("RetType")


class CloudProviderError(Exception):
    TYPE: str = "unclassified"

    def __init__(self, message: str) -> None:
        self.message = message

    def __str__(self) -> str:
        return f"{type(self).__name__}: {self.message} ({self.TYPE})"


class CloudProviderTemporaryFailure(CloudProviderError):
    TYPE: str = "temporary-failure"


class CloudProviderInstanceCountError(CloudProviderError):
    TYPE: str = "max-spot-instance-count-exceeded"


def wrap_provider_errors(wrapped: Callable[..., RetType]) -> Callable[..., RetType]:
    @functools.wraps(wrapped)
    def wrapper(*args: Any, **kwds: Any) -> RetType:
        try:
            return wrapped(*args, **kwds)
        except (ssl.SSLError, OSError) as exc:
            logging.getLogger("ec2spotmanager").exception("")
            raise CloudProviderTemporaryFailure(f"{wrapped.__name__}: {exc}")
        except CloudProviderError:
            logging.getLogger("ec2spotmanager").exception("")
            raise
        except Exception:
            logging.getLogger("ec2spotmanager").exception("")
            raise CloudProviderError(
                f"{wrapped.__name__}: unhandled error: {traceback.format_exc()}"
            )

    return wrapper


class CloudProvider(metaclass=ABCMeta):
    """
    Abstract base class that defines what interfaces Cloud Providers must implement
    """

    @abstractmethod
    def terminate_instances(self, instances_ids_by_region: dict[str, int]) -> None:
        """
        Take a list of running instances and stop them in the cloud provider.

        @param instances_ids_by_region: keys are regions and values are instances.
        """
        return

    @abstractmethod
    def cancel_requests(self, requested_instances_by_region: dict[str, int]) -> None:
        """
        Cancel requests that have not become running instances.

        @param requested_instances_region: keys are regions and values are request ids.
        """
        return

    @abstractmethod
    def start_instances(
        self,
        config: PoolConfiguration,
        region: str,
        zone: str,
        userdata,
        image: str,
        instance_type: str,
        count: int,
        tags: dict[str, str],
    ) -> None:
        """
        Start instances using specified configuration.

        @param config: flattened config. We use this for any cloud provider specific
                       fields needed to create an instance
        @param region: region where instances are to be started
        @param zone: zone the instances will be started in

        @ptype userdata: UserData object
        @param userdata: userdata script for instances
        @param image: image reference used to start instances
        @param instance_type: type of instance
        @param count: number of instances to start
        @param tags: instance tags.
        @return: Request IDs given to us by the cloud provider. This can be the instance
                 ID if the provider does not use different IDs for instances and
                 requests.
        """
        return

    @abstractmethod
    def check_instances_requests(
        self, region: str, instances: list[str], tags: dict[str, str]
    ) -> tuple[dict[str, str], dict[str, str]]:
        """
        Take a list of requested instances and determines the state of each instance.
        Since this is the first point we see an actual running instance
        we set the tags on the instances here as well.

        We create a dictionary of succesful requests. This has hostname,
        instance id, and status of each instance. This status must match the
        INSTANCE_STATE in CloudProvider.

        Failed requests will have an action and instance type. Currently, we
        support actions of 'blacklist' and disable_pool.

        @param region: the region the instances are in
        @param instances: instance request IDs
        @param tags: instance tags.
        @return: tuple containing 2 dicts: successful request IDs and failed request IDs
        """
        return

    @abstractmethod
    def check_instances_state(self, pool_id: int, region: str) -> None:
        """
        Takes a pool ID, searches the cloud provider for instances in that pool (using
        the tag) and returns a dictionary of instances with their state as value.

        @param list of pool instances are located in. We search for
        instances using the poolID tag
        @param region: region where instances are located
        @return: running instances and their states. State must comply with
                 INSTANCE_STATE defined in CloudProvider
        """
        return

    @abstractmethod
    def get_image(self, region: str, config: PoolConfiguration) -> str | None:
        """
        Takes a configuration and returns a provider specific image name.

        @param region: region
        @param config: flattened config
        @return: cloud provider ID for image
        """
        return

    @staticmethod
    @abstractmethod
    def get_cores_per_instance() -> dict[str, float]:
        """
        returns dictionary of instance types and their number of cores

        @return: instance types and how many cores per instance type
        """
        return

    @staticmethod
    @abstractmethod
    def get_allowed_regions(config: PoolConfiguration) -> list[str]:
        """
        Takes a configuration and returns cloud provider specific regions.

        @param config: pulling regions from config
        @return: regions pulled from config
        """
        return

    @staticmethod
    @abstractmethod
    def get_image_name(config: PoolConfiguration) -> str | None:
        """
        Takes a configuration and returns cloud provider specific image name.

        @param config: pulling image name from config
        @return: cloud specific image name from config
        """
        return

    @staticmethod
    @abstractmethod
    def get_instance_types(config: PoolConfiguration) -> str:
        """
        Takes a configuration and returns a list of cloud provider specific
        instance_types.

        @param config: pulling instance types from config
        @return: list of cloud specific instance_types from config
        """
        return

    @staticmethod
    @abstractmethod
    def get_max_price(config: PoolConfiguration) -> Decimal:
        """
        Takes a configuration and returns the cloud provider specific max_price.

        @param config: pulling max_price from config
        @return: cloud specific max_price
        """
        return

    @staticmethod
    @abstractmethod
    def get_tags(config: PoolConfiguration) -> str:
        """
        Takes a configuration and returns a dictionary of cloud provider specific tags.

        @param config: pulling tags field
        @return: cloud specific tags field
        """
        return

    @staticmethod
    @abstractmethod
    def get_name() -> str:
        """
        used to return name of cloud provider

        @return: string representation of the cloud provider
        """
        return

    @staticmethod
    @abstractmethod
    def config_supported(config: PoolConfiguration) -> bool:
        """Compares the fields provided in the config with those required by the cloud
        provider. If any field is missing, return False.

        @param config: Flattened config
        @return: True if all required cloud specific fields in config
        """
        return

    @abstractmethod
    def get_prices_per_region(
        self, region_name: str, instance_types: list[str] | None
    ) -> dict[str, dict[str, dict[str, float]]]:
        """
        takes region and instance_types and returns a dictionary of prices
        prices are stored with keys like 'provider:price:{instance-type}'
        and values {region: {zone (if used): [price value, ...]}}

        @param region_name: region to grab prices
        @param instance_types: list of instance_types
        @return: dictionary of prices as specified above.
        """
        return

    @staticmethod
    def get_instance(provider: str):
        """
        This is a method that is used to instantiate the provider class.
        """
        classname = provider + "CloudProvider"
        providerModule = __import__(
            f"ec2spotmanager.CloudProvider.{classname}", fromlist=[classname]
        )
        providerClass = getattr(providerModule, classname)
        return providerClass()
