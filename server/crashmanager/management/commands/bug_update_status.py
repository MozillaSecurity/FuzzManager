from django.core.management.base import NoArgsCommand
from crashmanager.models import Bug, BugProvider
from django.conf import settings
from crashmanager.management.common import mgmt_lock_required
import warnings

class Command(NoArgsCommand):
    help = "Check the status of all bugs we have"
    @mgmt_lock_required
    def handle_noargs(self, **options):      
        # Suppress warnings about native datetime vs. timezone
        warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*received a naive datetime.*")
        
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
                
                bug = providerBugs.filter(externalId=bugId)[0]
                if bugStatus[bugId] == None and bug.closed != None:
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
                elif bug.closed == None:
                    bug.closed = bugStatus[bugId]
                    bug.save()
                    