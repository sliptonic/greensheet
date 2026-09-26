"""
Send the daily summary to everyone who opted in. Run once a day from cron:

    0 7 * * *  cd /path/to/prototype && .venv/bin/python manage.py send_digests
"""

from django.core.management.base import BaseCommand

from sheets import services
from sheets.models import DigestSubscription


class Command(BaseCommand):
    help = "Send the opt-in daily summary for each greensheet."

    def handle(self, *args, **options):
        sent = skipped = 0
        subs = DigestSubscription.objects.filter(enabled=True, greensheet__archived_at__isnull=True).select_related(
            "greensheet", "person"
        )
        for sub in subs:
            if services.send_digest(sub):
                sent += 1
            else:
                skipped += 1
        self.stdout.write(f"sent {sent}, nothing to say for {skipped}")
