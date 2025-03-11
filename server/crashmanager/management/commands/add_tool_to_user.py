from django.core.management.base import BaseCommand
from django.contrib.auth.models import User as DjangoUser
from crashmanager.models import Tool, User as CrashManagerUser


class Command(BaseCommand):
    help = "Assigns a tool to a user's defaultToolsFilter using their username and ensures the user is restricted."

    def add_arguments(self, parser):
        parser.add_argument("username", help="The username to add the tool to")
        parser.add_argument("tool_name", help="Name of the tool to add")

    def handle(self, *args, **options):
        username = options["username"]
        tool_name = options["tool_name"]

        try:
            django_user = DjangoUser.objects.get(username=username)
        except DjangoUser.DoesNotExist:
            print(f"No user found with username '{username}'")
            return

        crash_manager_user = CrashManagerUser.get_or_create_restricted(django_user)[0]

        tool, created = Tool.objects.get_or_create(name=tool_name)
        if created:
            print(f"Tool '{tool_name}' was created.")

        # Ensure the user is restricted, so they can only access the tool being added
        if not crash_manager_user.restricted:
            crash_manager_user.restricted = True
            crash_manager_user.save()
            print(f"User '{username}' has been restricted for security.")

        crash_manager_user.defaultToolsFilter.add(tool)

        print(f"Tool '{tool_name}' added to user '{username}'.")
