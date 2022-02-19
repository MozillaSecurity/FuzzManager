from __future__ import annotations

from django.core.management.base import LabelCommand
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token


class Command(LabelCommand):

    help = "Provides the REST interface authentication token for the specified user(s)."

    def handle_label(self, label: str, **options: str) -> None:
        user = User.objects.get(username=label)

        (token, created) = Token.objects.get_or_create(user=user)

        if created:
            token.save()

        print(token.key)
