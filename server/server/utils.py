import logging
import time
import uuid
from ipaddress import (
    IPv4Address,
    IPv4Network,
    IPv6Address,
    IPv6Network,
    ip_address,
    ip_network,
)

import redis
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import PermissionDenied

LOG = logging.getLogger("fuzzmanager.utils")


def parse_bool(request, param, default=True):
    """Parse a boolean URL parameter.
    Accept "true", "false", "1", or "0", case insensitive.
    """
    param_value = request.query_params.get(param, str(default)).lower()
    assert param_value in {"true", "false", "1", "0"}
    return param_value in {"true", "1"}


class RedisLock:
    """Simple Redis mutex lock.

    based on: https://redislabs.com/ebook/part-2-core-concepts \
              /chapter-6-application-components-in-redis/6-2-distributed-locking \
              /6-2-3-building-a-lock-in-redis/

    Not using RedLock because it isn't passable as a celery argument, so we can't
    release the lock in an async chain.
    """

    def __init__(self, conn, name, unique_id=None):
        self.conn = conn
        self.name = name
        if unique_id is None:
            self.unique_id = str(uuid.uuid4())
        else:
            self.unique_id = unique_id

    def acquire(self, acquire_timeout=10, lock_expiry=None):
        end = time.time() + acquire_timeout
        while time.time() < end:
            if self.conn.set(self.name, self.unique_id, ex=lock_expiry, nx=True):
                LOG.debug("Acquired lock: %s(%s)", self.name, self.unique_id)
                return self.unique_id

            time.sleep(0.05)

        LOG.debug("Failed to acquire lock: %s(%s)", self.name, self.unique_id)
        return None

    def release(self):
        with self.conn.pipeline() as pipe:
            while True:
                try:
                    pipe.watch(self.name)
                    existing = pipe.get(self.name)
                    if not isinstance(existing, str):
                        existing = existing.decode("ascii")

                    if existing == self.unique_id:
                        pipe.multi()
                        pipe.delete(self.name)
                        pipe.execute()
                        LOG.debug("Released lock: %s(%s)", self.name, self.unique_id)
                        return True

                    pipe.unwatch()
                    break

                except redis.exceptions.WatchError:
                    pass

        LOG.debug(
            "Failed to release lock: %s(%s) != %s", self.name, self.unique_id, existing
        )
        return False


def get_client_ip(request):
    """
    Extracts the client IP address from request headers.
    """
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")

    return ip


class IPRestrictedTokenAuthentication(TokenAuthentication):
    def authenticate(self, request):
        auth_result = super().authenticate(request)

        # No need to check IP if authentication failed or no token was provided
        if not auth_result:
            return auth_result

        user, token = auth_result

        if not self.is_from_allowed_ip(request, token):
            LOG.warning(f"IP address restricted for token: {token.key[:8]}...")
            raise PermissionDenied("IP address restricted. Access denied.")

        return auth_result

    def is_from_allowed_ip(self, request, token):
        """
        Checks if the request IP is allowed for this token.
        """
        client_ip = get_client_ip(request)
        from .models import TokenIPRestriction

        ip_restrictions = TokenIPRestriction.objects.filter(token=token)

        # All users have open policy access by default
        if not ip_restrictions.exists():
            TokenIPRestriction.objects.create(token=token, ip_range="0.0.0.0/0")
            TokenIPRestriction.objects.create(token=token, ip_range="::/0")
            return True

        # First, try to parse the client IP as a valid IP address
        try:
            ip_obj = ip_address(client_ip)
        except ValueError:
            LOG.warning(f"Invalid IP address format: {client_ip}")
            return False

        # Check each restriction
        for restriction in ip_restrictions:
            try:
                # For network ranges, we use ip_network (which handles CIDR notation)
                network = ip_network(restriction.ip_range, strict=False)

                # Check if the IP is within the allowed range
                if (
                    isinstance(ip_obj, IPv4Address) and isinstance(network, IPv4Network)
                ) or (
                    isinstance(ip_obj, IPv6Address) and isinstance(network, IPv6Network)
                ):
                    if ip_obj in network:
                        return True

            except ValueError:
                LOG.warning(f"Invalid network definition: {restriction.ip_range}")
                continue

        return False
