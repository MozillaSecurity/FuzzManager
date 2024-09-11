from django.contrib.auth.models import User
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "List permissions granted to the specified user."

    def handle(self, *args, **options):
        user = User.objects.get(username=options["user"])
        for perm in user.user_permissions.all():
            print(f"{perm.codename} ({perm.name})")

    def add_arguments(self, parser):
        parser.add_argument("user")
