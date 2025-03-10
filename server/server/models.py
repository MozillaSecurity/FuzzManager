from django.db import models
from rest_framework.authtoken.models import Token
from ipaddress import IPv4Network, IPv6Network, AddressValueError
from django.db.models.signals import post_save
from django.dispatch import receiver

class TokenIPRestriction(models.Model):
    """
    Model to store IP restrictions for authentication tokens.
    Each token can have multiple allowed IP ranges in CIDR notation.
    """
    token = models.ForeignKey(Token, on_delete=models.CASCADE, related_name='ip_restrictions')
    # IP range in CIDR notation (e.g. 192.168.1.0/24)
    ip_range = models.CharField(max_length=50)
    
    class Meta:
        unique_together = ('token', 'ip_range')
    
    def save(self, *args, **kwargs):
        # Validate IP address on IPv4 an IPv6 before saving
        try:
            IPv4Network(self.ip_range)
        except AddressValueError:
            try:
                IPv6Network(self.ip_range)
            except AddressValueError:
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
