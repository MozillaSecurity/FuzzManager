from django.core.management import BaseCommand

from crashmanager.models import User


class Command(BaseCommand):
    help = "Remove the restricted flag from the specified user."

    def handle(self, *args, **options):
        user = User.objects.get(user__username=options["user"])
        if user.restricted:
            user.restricted = False
            user.save()
            print(f"{options['user']} is now unrestricted")
        else:
            print(f"{options['user']} was already unrestricted")

    def add_arguments(self, parser):
        parser.add_argument("user")
