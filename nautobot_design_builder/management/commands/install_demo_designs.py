"""Set up the demo designs git data source."""

from django.core.management.base import BaseCommand
from nautobot.extras.models import GitRepository


class Command(BaseCommand):
    """Create a git datasource pointed to the demo designs repo."""

    def add_arguments(self, parser):
        """Add the branch argument to the command."""
        parser.add_argument(
            "--branch",
            action="store",
            help="Specify which branch to use in the demo-design repository (default: main).",
            default="main",
        )

    def handle(self, *args, **options):
        """Handle the execution of the command."""
        GitRepository.objects.get_or_create(
            name="Demo Designs",
            defaults={
                "remote_url": "https://github.com/nautobot/demo-designs.git",
                "branch": options["branch"],
                "provided_contents": ["extras.job"],
            },
        )
