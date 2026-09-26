"""
Make the person with this email an operator, creating them if needed.
They sign in by magic link like everyone else; /admin then works.
"""

from django.core.management.base import BaseCommand

from sheets.models import Person


class Command(BaseCommand):
    help = "Grant operator (admin) access to an email address."

    def add_arguments(self, parser):
        parser.add_argument("email")

    def handle(self, email, **options):
        person, created = Person.objects.get_or_create_by_email(email)
        if not (person.is_staff and person.is_superuser):
            person.is_staff = True
            person.is_superuser = True
            person.save(update_fields=["is_staff", "is_superuser"])
        self.stdout.write(f"operator: {person.email}{' (created)' if created else ''}")
