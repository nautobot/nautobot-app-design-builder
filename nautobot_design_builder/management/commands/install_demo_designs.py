"""Set up the demo designs git data source."""

from django.core.management.base import BaseCommand

from nautobot.extras.models import GitRepository


class Command(BaseCommand):
    """Create a git datasource pointed to the demo designs repo."""

    def handle(self, *args, **options):
        """Handle the execution of the command."""
        GitRepository.objects.get_or_create(
            name="Demo Designs",
            defaults={
                "remote_url": "https://github.com/nautobot/demo-designs.git",
                "branch": "main",
                "provided_contents": ["extras.job"],
            },
        )
