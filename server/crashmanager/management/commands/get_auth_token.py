from __future__ import print_function

from django.core.management.base import LabelCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


class Command(LabelCommand):

    help = "Provides the REST interface authentication token for the specified user(s)."

    def handle_label(self, label, **options):
        user = User.objects.get(username=label)

        (token, created) = Token.objects.get_or_create(user=user)

        if created:
            token.save()

        print(token.key)
