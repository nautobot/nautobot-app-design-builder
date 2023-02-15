"""Management command to bootstrap development data for design builder plugin."""

from django.core.management.base import BaseCommand

from ...tests.util import populate_sample_data


class Command(BaseCommand):
    """Populate the database with sample data. This command is idempotent."""

    def handle(self, *args, **options):
        """Handle the execution of the populate command."""
        self.stdout.write("Attempting to populate sample data.")
        populate_sample_data()
        self.stdout.write(self.style.SUCCESS("Successfully populated database."))
