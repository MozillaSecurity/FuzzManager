from __future__ import print_function

from django.core.management import BaseCommand
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User, Permission

from crashmanager.management.common import mgmt_lock_required


class Command(BaseCommand):
    help = "Adds permissions to the specified user."

    @mgmt_lock_required
    def handle(self, *args, **options):
        user = User.objects.get(username=options['user'])

        for perm in options['permission']:
            model, perm = perm.split(':', 1)
            module, model = model.rsplit('.', 1)
            module = __import__(module, globals(), locals(), [model], 0)  # from module import model
            content_type = ContentType.objects.get_for_model(getattr(module, model))
            perm = Permission.objects.get(content_type=content_type, codename=perm)
            user.user_permissions.add(perm)
            print('user %s added permission %s:%s' % (user.username, model, perm))

        print('done')

    def add_arguments(self, parser):
        parser.add_argument('user')
        parser.add_argument('permission', nargs='+', choices=[
            'crashmanager.models.User:view_covmanager',
            'crashmanager.models.User:view_crashmanager',
            'crashmanager.models.User:view_ec2spotmanager',
            'crashmanager.models.User:view_taskmanager',
        ])
