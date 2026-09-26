"""
Load the scenario from startup.md so the prototype has something to show.
Prints sign-in links for both people.
"""

from datetime import date

from django.core.management.base import BaseCommand

from sheets import services
from sheets.models import Greensheet, Person


class Command(BaseCommand):
    help = "Create the tax engagement scenario with a requester and a fulfiller."

    def handle(self, *args, **options):
        dana, _ = Person.objects.get_or_create_by_email("dana@whitfieldcpa.example", "Dana Whitfield")
        marcus, _ = Person.objects.get_or_create_by_email("marcus.bell@example.com", "Marcus Bell")

        if Greensheet.objects.filter(requester=dana, name="2025 tax engagement").exists():
            self.stdout.write("Scenario already exists.")
        else:
            sheet = services.create_greensheet(
                dana,
                name="2025 tax engagement",
                fulfiller_email=marcus.email,
                fulfiller_name=marcus.name,
                contact_email=dana.email,
                contact_phone="(573) 555-0142",
            )
            services.add_item(
                sheet, dana,
                title="Sign the engagement letter sent to you by email",
                note="It arrived Sept 26 from DocuSign. Check your spam folder if you don't see it.",
                due_date=date(2026, 10, 3),
            )
            services.add_item(
                sheet, dana,
                title="Provide 2024 and 2025 tax returns and supporting documentation",
                note="Federal and state. W-2s, 1099s, and the K-1 from the partnership. "
                "Upload to the portal link in my email or bring paper copies to the office.",
                due_date=date(2026, 10, 10),
            )
            i3 = services.add_item(sheet, dana, title="Send contact information for your bookkeeper")
            services.add_item(sheet, dana, title="Send contact information for your attorney")
            services.add_item(
                sheet, dana, title="Confirm the mailing address for the finished return", due_date=date(2026, 10, 3)
            )
            services.complete_item(i3, marcus)
            self.stdout.write(f"Created greensheet {sheet.code}: {sheet.name}")

        self.stdout.write("")
        for person in (dana, marcus):
            link = services.issue_magic_link(person, "/", send=False)
            self.stdout.write(f"{person.display:<16} {link.absolute_url}")
        self.stdout.write("")
        self.stdout.write("Links work once and expire in 15 minutes. Run `manage.py seed` again for fresh ones.")
