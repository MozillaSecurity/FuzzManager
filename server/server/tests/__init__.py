import pytest
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.fixture
def fm_user():
    user = User.objects.create_user('fuzzmanager', 'test@example.com', 'test')
    user.password_raw = 'test'

    (token, created) = Token.objects.get_or_create(user=user)
    if created:
        token.save()

    user.token = token.key
    return user
