from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand


class Command(BaseCommand):
    help = "Adds permissions to the specified user."

    def handle(self, *args, **options):
        user = User.objects.get(username=options["user"])

        for perm in options["permission"]:
            model, perm = perm.split(":", 1)
            module, model = model.rsplit(".", 1)
            module = __import__(
                module, globals(), locals(), [model], 0
            )  # from module import model
            content_type = ContentType.objects.get_for_model(getattr(module, model))
            perm = Permission.objects.get(content_type=content_type, codename=perm)
            user.user_permissions.add(perm)
            print(f"user {user.username} added permission {model}:{perm}")

        print("done")

    def add_arguments(self, parser):
        parser.add_argument("user")
        parser.add_argument(
            "permission",
            nargs="+",
            choices=[
                "crashmanager.models.User:view_covmanager",
                "crashmanager.models.User:view_crashmanager",
                "crashmanager.models.User:view_ec2spotmanager",
                "crashmanager.models.User:view_taskmanager",
            ],
        )
