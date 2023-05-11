"""Base Design Job class definition."""
import logging
import sys
import traceback
from abc import ABC, abstractmethod
from os import path
import yaml

from django.db import transaction
from django.utils.functional import classproperty

from jinja2 import TemplateError

from nautobot.extras.jobs import Job

from design_builder.errors import DesignImplementationError
from design_builder.jinja2 import new_template_environment
from design_builder.logging import LoggingMixin
from design_builder.design import Builder


class DesignJob(Job, ABC, LoggingMixin):  # pylint: disable=too-many-instance-attributes
    """The base Design Job class that all specific Design Builder jobs inherit from.

    DesignJob is an abstract base class that all design implementations must implement.
    Any design that is to be included in the list of Jobs in Nautobot *must* include
    a Meta class.
    """

    @classmethod
    @abstractmethod
    def Meta(cls) -> Job.Meta:  # pylint: disable=invalid-name
        """Design jobs must provide either a Meta class method or a Meta class."""

    # TODO: This init can be removed once fixes have been made in core nautobot
    def __init__(self):  # pylint: disable=super-init-not-called
        """Initialize the design job."""
        # DO NOT CALL super().__init__(), it will raise an OSError for
        # designs loaded from GIT
        self.logger = logging.getLogger(__name__)
        self.creator: Builder = None

        # rendered designs
        self.designs = {}
        self.rendered = None
        self.request = None
        self.active_test = "main"
        self.failed = False
        self._job_result = None

        # Compile test methods and initialize results skeleton
        self.test_methods = []

        for method_name in dir(self):
            if method_name.startswith("test_") and callable(getattr(self, method_name)):
                self.test_methods.append(method_name)

    @classproperty
    def class_path(cls):  # pylint: disable=no-self-argument
        """Returns the path to the module containing this class.

        Returns:
            str: path to module containing the path
        """
        try:
            return super().class_path
        except RuntimeError:
            # Since this is an Abstract Base Class, the only way we'll
            # get here is if we're building docs and mkdocs is trying
            # to load the class path.
            return "/".join(["plugins", cls.__module__, cls.__name__])  # pylint: disable=no-member

    def post_implementation(self, context, creator: Builder):
        """Generic implementation of Nautobot post_implementation method for a job class.

        Since this is the abstract base class it is not used here and is just set to pass.
        Design Jobs that inherit from this base DesignJob class will usually have this method extended and overridden.
        """

    def post_run(self):
        """Method that will run after the main Nautobot job has executed."""
        if self.rendered:
            self.results["output"] = self.rendered

        self.results["designs"] = self.designs

    def render(self, context, filename):
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
        # Make sure the design is defined even if exceptions are raised
        try:
            self.rendered = self.render(context, design_file)
            design = yaml.safe_load(self.rendered)
            self.designs[design_file] = design
        except Exception as ex:
            raise ex

        # no need to save the rendered content if yaml loaded
        # it okay
        self.rendered = None
        return design

    def render_report(self, context, journal):
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
        self.creator.implement_design(design, commit)

    @transaction.atomic
    def run(self, data, commit):
        """Render the design and implement it with ObjectCreator."""
        self.log_info(message=f"Building {getattr(self.Meta, 'name')}")
        extensions = getattr(self.Meta, "extensions", [])
        self.creator = Builder(job_result=self.job_result, extensions=extensions)

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
            self.failed = True
            return

        sid = transaction.savepoint()
        try:
            for design_file in design_files:
                self.implement_design(context, design_file, commit)
            if commit:
                self.creator.commit()
                self.post_implementation(context, self.creator)

                if hasattr(self.Meta, "report"):
                    self.results["report"] = self.render_report(context, self.creator.journal)
                    self.log_success(message=self.results["report"])
            else:
                self.log_info(
                    message=f"{self.name} can be imported successfully - No database changes made",
                )
        except DesignImplementationError as ex:
            transaction.savepoint_rollback(sid)
            self.log_failure(message=f"Failed to implement design: {ex}")
            self.failed = True
        except Exception as ex:
            transaction.savepoint_rollback(sid)
            raise ex
