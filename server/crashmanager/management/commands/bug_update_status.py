from django.conf import settings
from django.core.management import BaseCommand, CommandError

from crashmanager.management.common import mgmt_lock_required
from crashmanager.models import Bug, BugProvider


class Command(BaseCommand):
    help = "Check the status of all bugs we have"

    @mgmt_lock_required
    def handle(self, *args, **options):
        if args:
            raise CommandError("Command doesn't accept any arguments")

        providers = BugProvider.objects.all()
        for provider in providers:
            providerInstance = provider.getInstance()
            providerBugs = Bug.objects.filter(externalType=provider)
            bugIds = list(providerBugs.values_list('externalId', flat=True))

            if not bugIds:
                continue

            username = getattr(settings, 'BUGZILLA_USERNAME', None)
            password = getattr(settings, 'BUGZILLA_PASSWORD', None)

            bugStatus = providerInstance.getBugStatus(bugIds, username, password)

            if not bugStatus:
                raise RuntimeError("Error getting bug status from bug provider.")

            # Map to memorize which bugs we have duped to others
            bugDupMap = {}

            for bugId in bugStatus:
                # It is possible that two buckets are linked to one bug which has been marked
                # as a duplicate of another. Once the first bug has been processed, we don't
                # need to process any more bugs with the same bug id.
                if bugId in bugDupMap:
                    continue

                # Due to how duplicating bugs works, we can end up having multiple bug objects
                # with the same external bug id. Make sure we consider all of them.
                bugs = providerBugs.filter(externalId=bugId)
                for bug in bugs:
                    if bugStatus[bugId] is None and bug.closed is not None:
                        bug.closed = None
                        bug.save()
                    elif isinstance(bugStatus[bugId], str):
                        # The bug has been marked as a duplicate, so we change the externalId
                        # to match the duped bug. If that bug is also closed, then it will be
                        # picked up the next time this command runs.
                        bugDupMap[bug.externalId] = bugStatus[bugId]
                        bug.externalId = bugStatus[bugId]
                        bug.closed = None
                        bug.save()
                    elif bug.closed is None:
                        bug.closed = bugStatus[bugId]
                        bug.save()
