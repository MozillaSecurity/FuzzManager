from ipaddress import AddressValueError, IPv4Network, IPv6Network

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token


class TokenIPRestriction(models.Model):
    """
    Model to store IP restrictions for authentication tokens.
    Each token can have multiple allowed IP ranges in CIDR notation.
    """

    token = models.ForeignKey(
        Token, on_delete=models.CASCADE, related_name="ip_restrictions"
    )
    # IP range in CIDR notation (e.g. 192.168.1.0/24)
    ip_range = models.CharField(max_length=50)

    class Meta:
        unique_together = ("token", "ip_range")

    @staticmethod
    def validate_cidr(cidr):
        """
        Validate if a string is a valid CIDR notation for either IPv4 or IPv6.
        Returns True if valid, False otherwise.
        """
        try:
            IPv4Network(cidr)
            return True
        except (AddressValueError, ValueError):
            try:
                IPv6Network(cidr)
                return True
            except (AddressValueError, ValueError):
                return False

    def save(self, *args, **kwargs):
        if not self.validate_cidr(self.ip_range):
            raise ValueError(f"Invalid CIDR notation: {self.ip_range}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.token.key[:8]}... - {self.ip_range}"


@receiver(post_save, sender=Token)
def create_default_ip_restriction(sender, instance, created, **kwargs):
    """
    Ensures that all newly created tokens have a default open policy.
    """
    if created:
        # Use 0.0.0.0/0 as the default to allow all IPv4 addresses
        TokenIPRestriction.objects.create(token=instance, ip_range="0.0.0.0/0")
        # Also allow all IPv6 addresses
        TokenIPRestriction.objects.create(token=instance, ip_range="::/0")
