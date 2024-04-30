"""Base Design Job class definition."""

import sys
import traceback
from abc import ABC, abstractmethod
from os import path
from typing import Dict
import yaml

from django.db import transaction
from django.core.files.base import ContentFile

from jinja2 import TemplateError

from nautobot.apps.jobs import Job, DryRunVar
from nautobot.extras.models import FileProxy

from nautobot_design_builder.errors import DesignImplementationError, DesignModelError
from nautobot_design_builder.jinja2 import new_template_environment
from nautobot_design_builder.logging import LoggingMixin
from nautobot_design_builder.design import Environment
from nautobot_design_builder.context import Context


class DesignJob(Job, ABC, LoggingMixin):  # pylint: disable=too-many-instance-attributes
    """The base Design Job class that all specific Design Builder jobs inherit from.

    DesignJob is an abstract base class that all design implementations must implement.
    Any design that is to be included in the list of Jobs in Nautobot *must* include
    a Meta class.
    """

    dryrun = DryRunVar()

    @classmethod
    @abstractmethod
    def Meta(cls) -> Job.Meta:  # pylint: disable=invalid-name
        """Design jobs must provide either a Meta class method or a Meta class."""

    def __init__(self, *args, **kwargs):
        """Initialize the design job."""
        # rendered designs
        self.environment: Environment = None
        self.designs = {}
        self.rendered_design = None
        self.rendered = None

        super().__init__(*args, **kwargs)

    def post_implementation(self, context: Context, environment: Environment):
        """Similar to Nautobot job's `post_run` method, but will be called after a design is implemented.

        Any design job that requires additional work to be completed after the design
        has been implemented can provide a `post_implementation` method. This method will be
        called after the entire set of design files has been implemented and the database
        transaction has been committed.

        Args:
            context (Context): The render context that was used for rendering the design files.
            environment (Environment): The build environment that consumed the rendered design files. This is useful for accessing the design journal.
        """

    def render(self, context: Context, filename: str) -> str:
        """High level function to render the Jinja design templates into YAML.

        Args:
            context (Context object): a tree of variables that can include templates for values
            filename (str): file name of the Jinja design template

        Raises:
            ex: If there are any rendering errors raise a TemplateError but also include the traceback, Jinja file name and line numbers

        Returns:
            str: YAML data structure rendered from input Jinja template
        """
        search_paths = []
        cls = self.__class__
        # We pass a list of directories to the jinja template environment
        # to be used for search paths in the FileSystemLoader. This list
        # of paths is compiled from the directory location of the current
        # design job and its entire inheritance tree. In order to produce
        # this list, we traverse the inheritance tree upwards until we
        # get to the toplevel base class, `DesignJob`
        while cls is not DesignJob:
            class_dir = path.dirname(sys.modules[cls.__module__].__file__)
            search_paths.append(class_dir)
            cls = cls.__bases__[0]

        env = new_template_environment(context, search_paths)

        try:
            return env.get_template(filename).render()
        except TemplateError as ex:
            info = sys.exc_info()[2]
            summary = traceback.extract_tb(info, -1)[0]
            self.log_failure(message=f"{filename}:{summary.lineno}")
            raise ex

    def render_design(self, context, design_file):
        """Wrapper function to take in rendered YAML from the design and convert to structured data and assign to the design property of a class instance.

        Args:
            context (Context object): a tree of variables that can include templates for values
            design_file (str): Filename of the design file to render.
        """
        self.rendered_design = design_file
        self.rendered = self.render(context, design_file)
        design = yaml.safe_load(self.rendered)
        self.designs[design_file] = design

        # no need to save the rendered content if yaml loaded
        # it okay
        self.rendered_design = None
        self.rendered = None
        return design

    def render_report(self, context: Context, journal: Dict) -> str:
        """Wrapper function to create rendered markdown report from the design job's Jinja report template.

        Args:
            context (Context object): a tree of variables that can include templates for values
            journal (dict): A dictionary containing keys matching to ORM classes containing lists of Nautobot objects that were created by the design job

        Returns:
            str: job report data in markdown format
        """
        return self.render(
            {
                "context": context,
                "journal": journal,
            },
            getattr(self.Meta, "report"),
        )

    def implement_design(self, context, design_file, commit):
        """Render the design_file template using the provided render context."""
        design = self.render_design(context, design_file)
        self.environment.implement_design(design, commit)

    def run(self, dryrun: bool, **kwargs):  # pylint: disable=arguments-differ
        """Render the design and implement it within a build Environment object."""
        try:
            return self._run_in_transaction(dryrun, **kwargs)
        finally:
            if self.rendered:
                rendered_design = path.basename(self.rendered_design)
                rendered_design, _ = path.splitext(rendered_design)
                if not rendered_design.endswith(".yaml") and not rendered_design.endswith(".yml"):
                    rendered_design = f"{rendered_design}.yaml"
                self.save_design_file(rendered_design, self.rendered)
            for design_file, design in self.designs.items():
                output_file = path.basename(design_file)
                # this should remove the .j2
                output_file, _ = path.splitext(output_file)
                if not output_file.endswith(".yaml") and not output_file.endswith(".yml"):
                    output_file = f"{output_file}.yaml"
                self.save_design_file(output_file, yaml.safe_dump(design))

    @transaction.atomic
    def _run_in_transaction(self, dryrun: bool, **data):  # pylint: disable=too-many-branches
        """Render the design and implement it within a build Environment object.

        This version of `run` is wrapped in a transaction and will roll back database changes
        on error. In general, this method should only be called by the `run` method.
        """
        self.log_info(message=f"Building {getattr(self.Meta, 'name')}")
        extensions = getattr(self.Meta, "extensions", [])
        self.environment = Environment(job_result=self.job_result, extensions=extensions)

        design_files = None

        if hasattr(self.Meta, "context_class"):
            context = self.Meta.context_class(data=data, job_result=self.job_result)
            context.validate()
        else:
            context = {}

        if hasattr(self.Meta, "design_file"):
            design_files = [self.Meta.design_file]
        elif hasattr(self.Meta, "design_files"):
            design_files = self.Meta.design_files
        else:
            self.log_failure(message="No design template specified for design.")
            raise DesignImplementationError("No design template specified for design.")

        sid = transaction.savepoint()

        try:
            for design_file in design_files:
                self.implement_design(context, design_file, not dryrun)
            if not dryrun:
                self.post_implementation(context, self.environment)
                if hasattr(self.Meta, "report"):
                    report = self.render_report(context, self.environment.journal)
                    output_filename: str = path.basename(getattr(self.Meta, "report"))
                    if output_filename.endswith(".j2"):
                        output_filename = output_filename[0:-3]
                    self.log_success(message=report)
                    self.save_design_file(output_filename, report)
            else:
                transaction.savepoint_rollback(sid)
                self.log_info(
                    message=f"{self.name} can be imported successfully - No database changes made",
                )
        except (DesignImplementationError, DesignModelError) as ex:
            transaction.savepoint_rollback(sid)
            self.log_failure(message="Failed to implement design")
            self.log_failure(message=str(ex))
            raise ex
        except Exception as ex:
            transaction.savepoint_rollback(sid)
            raise ex

    def save_design_file(self, filename, content):
        """Save some content to a job file.

        This is only supported on Nautobot 2.0 and greater.

        Args:
            filename (str): The name of the file to save.
            content (str): The content to save to the file.
        """
        FileProxy.objects.create(
            name=filename,
            job_result=self.job_result,
            file=ContentFile(content.encode("utf-8"), name=filename),
        )
