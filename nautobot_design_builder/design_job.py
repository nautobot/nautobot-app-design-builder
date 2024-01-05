"""Base Design Job class definition."""
import sys
import traceback
from abc import ABC, abstractmethod
from os import path
from typing import Dict
import yaml

from django.db import transaction

from jinja2 import TemplateError

from nautobot.extras.jobs import Job


from nautobot_design_builder.errors import DesignImplementationError, DesignModelError
from nautobot_design_builder.jinja2 import new_template_environment
from nautobot_design_builder.logging import LoggingMixin
from nautobot_design_builder.design import Builder
from nautobot_design_builder.context import Context
from .util import nautobot_version


class DesignJob(Job, ABC, LoggingMixin):  # pylint: disable=too-many-instance-attributes
    """The base Design Job class that all specific Design Builder jobs inherit from.

    DesignJob is an abstract base class that all design implementations must implement.
    Any design that is to be included in the list of Jobs in Nautobot *must* include
    a Meta class.
    """

    if nautobot_version >= "2.0.0":
        from nautobot.extras.jobs import DryRunVar  # pylint: disable=no-name-in-module,import-outside-toplevel

        dryrun = DryRunVar()

    @classmethod
    @abstractmethod
    def Meta(cls) -> Job.Meta:  # pylint: disable=invalid-name
        """Design jobs must provide either a Meta class method or a Meta class."""

    def __init__(self, *args, **kwargs):
        """Initialize the design job."""
        # rendered designs
        self.builder: Builder = None
        self.designs = {}
        self.rendered = None
        self.failed = False

        super().__init__(*args, **kwargs)

    def post_implementation(self, context: Context, builder: Builder):
        """Similar to Nautobot job's `post_run` method, but will be called after a design is implemented.

        Any design job that requires additional work to be completed after the design
        has been implemented can provide a `post_implementation` method. This method will be
        called after the entire set of design files has been implemented and the database
        transaction has been committed.

        Args:
            context (Context): The render context that was used for rendering the design files.
            builder (Builder): The builder object that consumed the rendered design files. This is useful for accessing the design journal.
        """

    def post_run(self):
        """Method that will run after the main Nautobot job has executed."""
        if self.rendered:
            self.job_result.data["output"] = self.rendered

        self.job_result.data["designs"] = self.designs

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
        self.rendered = self.render(context, design_file)
        design = yaml.safe_load(self.rendered)
        self.designs[design_file] = design

        # no need to save the rendered content if yaml loaded
        # it okay
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
        self.builder.implement_design(design, commit)

    @transaction.atomic
    def run(self, **kwargs):  # pylint: disable=arguments-differ,too-many-branches
        """Render the design and implement it with a Builder object."""
        self.log_info(message=f"Building {getattr(self.Meta, 'name')}")
        extensions = getattr(self.Meta, "extensions", [])
        self.builder = Builder(job_result=self.job_result, extensions=extensions)

        design_files = None

        if nautobot_version < "2.0.0":
            commit = kwargs["commit"]
            data = kwargs["data"]
        else:
            commit = not kwargs.pop("dryrun", True)
            data = kwargs

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
            self.failed = True
            return

        sid = transaction.savepoint()

        try:
            for design_file in design_files:
                self.implement_design(context, design_file, commit)
            if commit:
                self.post_implementation(context, self.builder)
                if hasattr(self.Meta, "report"):
                    self.job_result.data["report"] = self.render_report(context, self.builder.journal)
                    self.log_success(message=self.job_result.data["report"])
            else:
                transaction.savepoint_rollback(sid)
                self.log_info(
                    message=f"{self.name} can be imported successfully - No database changes made",
                )
        except (DesignImplementationError, DesignModelError) as ex:
            transaction.savepoint_rollback(sid)
            self.log_failure(message="Failed to implement design")
            self.log_failure(message=str(ex))
            self.failed = True
        except Exception as ex:
            transaction.savepoint_rollback(sid)
            self.failed = True
            raise ex
