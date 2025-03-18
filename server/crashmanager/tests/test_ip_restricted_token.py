import pytest
from rest_framework.authtoken.models import Token

from server.models import TokenIPRestriction

from .conftest import _create_user


@pytest.fixture
def token_with_ip_restriction(api_client):
    """Create a user with a token that has IP restrictions"""
    user = _create_user("test")
    token = Token.objects.create(user=user)

    # Delete default restrictions to have a clean state
    TokenIPRestriction.objects.filter(token=token).delete()

    # Add a restriction and verify it's the only one
    TokenIPRestriction.objects.create(token=token, ip_range="192.168.1.0/24")
    assert TokenIPRestriction.objects.filter(token=token).count() == 1

    # Add token to request headers
    api_client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    return token


@pytest.mark.django_db
def test_allowed_ip_can_authenticate(api_client, token_with_ip_restriction):
    """Ensure authentication works for an allowed IP"""
    response = api_client.get(
        "/crashmanager/rest/crashes/", REMOTE_ADDR="192.168.1.100"
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_blocked_ip_is_rejected(api_client, token_with_ip_restriction):
    """Ensure authentication fails for an unauthorized IP"""
    response = api_client.get("/crashmanager/rest/crashes/", REMOTE_ADDR="203.0.113.10")

    assert response.status_code == 403
    assert response.json()["detail"] == "IP address restricted. Access denied."
