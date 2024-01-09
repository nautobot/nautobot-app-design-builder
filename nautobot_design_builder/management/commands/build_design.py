"""Management command to bootstrap development data for design builder app."""
import sys
import yaml

from django.core.management.base import BaseCommand, CommandError

from ...design import Builder


def _load_file(filename):
    if filename == "-":
        return yaml.safe_load(sys.stdin)
    try:
        with open(filename) as file:  # pylint: disable=unspecified-encoding
            return yaml.safe_load(file)
    except FileNotFoundError as ex:
        # pylint: disable=raise-missing-from
        raise CommandError(str(ex))


class Command(BaseCommand):
    """Build all the Nautobot objects defined by a fully populated design design YAML."""

    def add_arguments(self, parser):
        """Adds the design_file argument to the required command arguments."""
        parser.add_argument("--commit", action="store_true", help="Commit the design to the database.")
        parser.add_argument("design_file", nargs="+", type=str)

    def handle(self, *args, **options):
        """Handle the execution of the command."""
        builder = Builder()
        for filename in options["design_file"]:
            self.stdout.write(f"Building design from {filename}")
            design = _load_file(filename)
            builder.implement_design(design, commit=options["commit"])
