from django.conf import settings
from django.contrib.auth.models import User as DjangoUser
from django.core.management import BaseCommand

from crashmanager.models import User


class Command(BaseCommand):
    help = "Create a user and prompt for a new password"

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)

    def handle(self, *_args, **options):
        User.objects.create(
            user=DjangoUser.objects.create(
                username=options["username"], email=options["email"]
            ),
            restricted=getattr(settings, "USERS_RESTRICTED_BY_DEFAULT", False),
        )
