from django.contrib.auth.models import User as DjangoUser
from django.core.management.base import BaseCommand

from crashmanager.models import Tool
from crashmanager.models import User as CrashManagerUser


class Command(BaseCommand):
    help = "Removes a tool from a user's defaultToolsFilter using their username."

    def add_arguments(self, parser):
        parser.add_argument("username", help="The username to remove the tool from")
        parser.add_argument("tool_name", help="Name of the tool to remove")

    def handle(self, *args, **options):
        username = options["username"]
        tool_name = options["tool_name"]

        try:
            django_user = DjangoUser.objects.get(username=username)
        except DjangoUser.DoesNotExist:
            print(f"No user found with username '{username}'")
            return

        crash_manager_user = CrashManagerUser.get_or_create_restricted(django_user)[0]

        try:
            tool = Tool.objects.get(name=tool_name)
        except Tool.DoesNotExist:
            print(f"Error: Tool '{tool_name}' is not present in the database")
            return

        crash_manager_user.defaultToolsFilter.remove(tool)

        # Keep user restricted regardless of tool count
        if not crash_manager_user.restricted:
            crash_manager_user.restricted = True
            crash_manager_user.save()
        if not crash_manager_user.defaultToolsFilter.exists():
            print(f"User '{username}' has no tools assigned but remains restricted.")

        print(f"Tool '{tool_name}' removed from user '{username}'.")
