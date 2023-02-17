"""Management command to bootstrap development data for design builder plugin."""
import sys
import yaml

from django.core.management.base import BaseCommand, CommandError

from ...design import Builder

class Command(BaseCommand):
    """Build all the Nautobot objects defined by a fully populated design design YAML."""

    def add_arguments(self, parser):
        parser.add_argument('design_file', nargs='+', type=str)

    def load_file(self, filename):
        if filename == "-":
            return yaml.safe_load(sys.stdin)
        try:
            with open(filename) as file:
                return yaml.safe_load(file)
        except FileNotFoundError as ex:
            raise CommandError(str(ex))

    def handle(self, *args, **options):
        """Handle the execution of the command."""
        builder = Builder()
        for filename in options["design_file"]:
            self.stdout.write(f"Building design from {filename}")
            design = self.load_file(filename)
            builder.implement_design(design)
