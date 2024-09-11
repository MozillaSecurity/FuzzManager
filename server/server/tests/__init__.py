import pytest
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from rest_framework.authtoken.models import Token

from reportmanager.models import User as CMUser

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def fm_user():
    user = User.objects.create_user("fuzzmanager", "test@example.com", "test")
    content_type = ContentType.objects.get_for_model(CMUser)
    user.user_permissions.add(
        Permission.objects.get(content_type=content_type, codename="view_reportmanager")
    )
    user.user_permissions.add(
        Permission.objects.get(content_type=content_type, codename="reportmanager_all")
    )
    user.password_raw = "test"

    (token, created) = Token.objects.get_or_create(user=user)
    if created:
        token.save()

    user.token = token.key
    return user
