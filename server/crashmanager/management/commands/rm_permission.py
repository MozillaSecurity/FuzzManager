from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand

from crashmanager.models import User as cmUser


class Command(BaseCommand):
    help = "Remove permissions from the specified user."

    def handle(self, *args, **options):
        user = User.objects.get(username=options["user"])

        for perm in options["permission"]:
            content_type = ContentType.objects.get_for_model(cmUser)
            perm = Permission.objects.get(content_type=content_type, codename=perm)
            user.user_permissions.remove(perm)
            print(f"user {user.username} removed permission {perm}")

        print("done")

    def add_arguments(self, parser):
        parser.add_argument("user")
        parser.add_argument(
            "permission",
            nargs="+",
            choices=dict(cmUser._meta.permissions),
        )
