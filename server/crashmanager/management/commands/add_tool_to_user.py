from django.contrib.auth.models import User as DjangoUser
from django.core.management.base import BaseCommand, CommandError

from crashmanager.models import Tool
from crashmanager.models import User as CrashManagerUser


class Command(BaseCommand):
    help = "Assigns a tool to a user's defaultToolsFilter using their username."

    def add_arguments(self, parser):
        parser.add_argument("username", help="The username to add the tool to")
        parser.add_argument(
            "tool_name",
            help="Name of the tool to add",
            choices=Tool.objects.all().values_list("name", flat=True),
        )

    def handle(self, *args, **options):
        username = options["username"]
        tool_name = options["tool_name"]

        try:
            django_user = DjangoUser.objects.get(username=username)
        except DjangoUser.DoesNotExist:
            raise CommandError(f"No user found with username '{username}'")

        crash_manager_user = CrashManagerUser.get_or_create_restricted(django_user)[0]

        tool, created = Tool.objects.get_or_create(name=tool_name)
        if created:
            self.stdout.write(f"Tool '{tool_name}' was created.")

        crash_manager_user.defaultToolsFilter.add(tool)

        self.stdout.write(f"Tool '{tool_name}' added to user '{username}'.")
