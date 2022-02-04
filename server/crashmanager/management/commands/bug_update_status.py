from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand, CommandError
from notifications.models import Notification
from notifications.signals import notify

from crashmanager.models import Bug, BugProvider


class Command(BaseCommand):
    help = "Check the status of all bugs we have"

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

            bug_content_type = ContentType.objects.get(model="bug")
            for bugId in bugIds:
                if int(bugId) not in bugStatus:
                    bugs = providerBugs.filter(externalId=bugId)
                    for bug in bugs:
                        # Listing all notifications sent to alert that this specific bug is inaccessible
                        sent_notifications_ids = Notification.objects.filter(
                            verb="inaccessible_bug",
                            actor_content_type=bug_content_type,
                            actor_object_id=bug.id,
                            target_content_type=bug_content_type,
                            target_object_id=bug.id,
                        ).values_list('id', flat=True)
                        # Exluding users who have already receive this notification
                        recipient = bug.tools_filter_users.exclude(notifications__id__in=sent_notifications_ids)
                        notify.send(
                            bug,
                            recipient=recipient,
                            actor=bug,
                            verb="inaccessible_bug",
                            target=bug,
                            level="info",
                            description=f"The bucket {bug.bucket_set.get().id} assigned to the external bug "
                                        f"{bug.externalId} on {provider.hostname} has become inaccessible"
                        )
