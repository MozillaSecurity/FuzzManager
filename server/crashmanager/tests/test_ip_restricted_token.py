import pytest
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
import requests

@pytest.fixture
def allowed_ip():
    return "127.0.0.1"

@pytest.fixture
def blocked_ip():
    return "203.0.113.10"

@pytest.mark.django_db
def test_allowed_ip_can_authenticate(api_client, user_normal, allowed_ip):
    """Ensure authentication works for an allowed IP"""
    response = api_client.get("/crashmanager/rest/crashes/", REMOTE_ADDR=allowed_ip)
    assert response.status_code == 200

@pytest.mark.django_db
def test_blocked_ip_is_rejected(api_client, allowed_ip, blocked_ip):
    """Ensure authentication fails for a blocked IP"""
    response = api_client.get("/crashmanager/rest/crashes/", REMOTE_ADDR=blocked_ip)
    assert response.status_code == 403
    assert response.json()['detail'] == 'IP address restricted. Access denied.'

