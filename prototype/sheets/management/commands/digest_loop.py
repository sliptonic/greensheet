"""
Sleep until the next GREENSHEET_DIGEST_HOUR (local time), send digests,
repeat. Used by the container entrypoint so no external cron is needed.
"""

import os
import time
from datetime import datetime, timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Run send_digests once a day, forever."

    def handle(self, *args, **options):
        hour = int(os.environ.get("GREENSHEET_DIGEST_HOUR", "7"))
        while True:
            now = timezone.localtime()
            nxt = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if nxt <= now:
                nxt += timedelta(days=1)
            wait = (nxt - now).total_seconds()
            self.stdout.write(f"digest_loop: next run {nxt:%Y-%m-%d %H:%M %Z} ({int(wait)}s)")
            time.sleep(wait)
            try:
                call_command("send_digests")
            except Exception as e:  # keep the loop alive
                self.stderr.write(f"digest_loop: {e}")
