from django.core.mail import send_mail
from django.core.management import BaseCommand
from django.template.loader import render_to_string
from notifications.models import Notification

from crashmanager.management.common import mgmt_lock_required
from crashmanager.models import User


class Command(BaseCommand):
    help = "Send notifications by email."

    @mgmt_lock_required
    def handle(self, *args, **options):
        # Select all notifications that haven't been sent by email for now
        notifications = Notification.objects.filter(emailed=False)
        for notification in notifications:
            try:
                user = User.objects.get(user=notification.recipient)
            except User.DoesNotExist:
                continue

            if not user.user.email:
                print(f'No user email for {user.user.username}')
                continue
            if notification.verb == "bucket_hit" and not user.bucket_hit:
                print(f'{user.user.username} not watching bucket_hit anymore')
                continue
            if notification.verb == "inaccessible_bug" and not user.inaccessible_bug:
                print(f'{user.user.username} not watching inaccessible_bug anymore')
                continue

            sent = send_mail(
                subject=f"New '{notification.verb}' notification",
                message=render_to_string(
                    'notification_mail.html',
                    context={
                        'user': user,
                        'notification': notification,
                    },
                ),
                from_email=None,
                recipient_list=[user.user.email],
                fail_silently=True,
            )
            if sent == 0:
                print(f"Failed to send notification email to {user.user.email}")
                continue

            notification.emailed = True
            notification.save()
