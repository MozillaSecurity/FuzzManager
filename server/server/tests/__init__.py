import pytest
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Permission
from rest_framework.authtoken.models import Token
from crashmanager.models import User as CMUser

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def fm_user():
    user = User.objects.create_user('fuzzmanager', 'test@example.com', 'test')
    content_type = ContentType.objects.get_for_model(CMUser)
    user.user_permissions.add(Permission.objects.get(content_type=content_type, codename='view_ec2spotmanager'))
    user.user_permissions.add(Permission.objects.get(content_type=content_type, codename='view_crashmanager'))
    user.user_permissions.add(Permission.objects.get(content_type=content_type, codename='view_taskmanager'))
    user.password_raw = 'test'

    (token, created) = Token.objects.get_or_create(user=user)
    if created:
        token.save()

    user.token = token.key
    return user
