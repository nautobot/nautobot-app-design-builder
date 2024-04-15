"""Base Design Job class definition."""

import sys
import copy
import traceback
from abc import ABC, abstractmethod
from os import path
from datetime import datetime
from typing import Dict
import yaml
from django.db import transaction
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile

from jinja2 import TemplateError

from nautobot.extras.models import Status
from nautobot.extras.jobs import Job, StringVar
from nautobot.extras.models import FileProxy

from nautobot_design_builder.errors import DesignImplementationError, DesignModelError
from nautobot_design_builder.jinja2 import new_template_environment
from nautobot_design_builder.logging import LoggingMixin
from nautobot_design_builder.design import Environment
from nautobot_design_builder.context import Context
from nautobot_design_builder import models
from nautobot_design_builder import choices
from nautobot_design_builder.recursive import combine_designs

from .util import nautobot_version


class DesignJob(Job, ABC, LoggingMixin):  # pylint: disable=too-many-instance-attributes
    """The base Design Job class that all specific Design Builder jobs inherit from.

    DesignJob is an abstract base class that all design implementations must implement.
    Any design that is to be included in the list of Jobs in Nautobot *must* include
    a Meta class.
    """

    instance_name = StringVar(label="Instance Name", max_length=models.DESIGN_NAME_MAX_LENGTH)

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
        self.environment: Environment = None
        self.designs = {}
        # TODO: Remove this when we no longer support Nautobot 1.x
        self.rendered = None
        self.rendered_design = None
        self.failed = False
        self.report = None

        super().__init__(*args, **kwargs)

    def design_model(self):
        """Get the related Job."""
        return models.Design.objects.for_design_job(self.job_result.job_model)

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

    def post_run(self):
        """Method that will run after the main Nautobot job has executed."""
        # TODO: This is not supported in Nautobot 2 and the entire method
        # should be removed once we no longer support Nautobot 1.
        if self.rendered:
            self.job_result.data["output"] = self.rendered

        self.job_result.data["designs"] = self.designs
        self.job_result.data["report"] = self.report

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
        """Render the design_file template using the provided render context.

        It considers reduction if a previous design instance exists.
        """
        design = self.render_design(context, design_file)
        self.log_debug(f"New Design to be implemented: {design}")
        deprecated_design = {}

        # The design to apply will take into account the previous journal that keeps track (in the builder_output)
        # of the design used (i.e., the YAML) including the Nautobot IDs that will help to reference them
        self.environment.builder_output[design_file] = copy.deepcopy(design)
        last_journal = (
            self.environment.journal.design_journal.design_instance.journals.filter(active=True)
            .exclude(id=self.environment.journal.design_journal.id)
            .exclude(builder_output={})
            .order_by("-last_updated")
            .first()
        )
        if last_journal and last_journal.builder_output:
            # The last design output is used as the reference to understand what needs to be changed
            # The design output store the whole set of attributes, not only the ones taken into account
            # in the implementation
            previous_design = last_journal.builder_output[design_file]
            self.log_debug(f"Design from previous Journal: {previous_design}")

            for key, new_value in design.items():
                old_value = previous_design[key]
                future_value = self.environment.builder_output[design_file][key]
                combine_designs(new_value, old_value, future_value, deprecated_design, key)

            self.log_debug(f"Design to implement after reduction: {design}")
            self.log_debug(f"Design to deprecate after reduction: {deprecated_design}")

        self.environment.implement_design(design, deprecated_design, design_file, commit)

    def _setup_journal(self, instance_name: str):
        try:
            instance = models.DesignInstance.objects.get(name=instance_name, design=self.design_model())
            self.log_info(message=f'Existing design instance of "{instance_name}" was found, re-running design job.')
            instance.last_implemented = datetime.now()
        except models.DesignInstance.DoesNotExist:
            self.log_info(message=f'Implementing new design "{instance_name}".')
            content_type = ContentType.objects.get_for_model(models.DesignInstance)
            instance = models.DesignInstance(
                name=instance_name,
                design=self.design_model(),
                last_implemented=datetime.now(),
                status=Status.objects.get(content_types=content_type, name=choices.DesignInstanceStatusChoices.ACTIVE),
                live_state=Status.objects.get(
                    content_types=content_type, name=choices.DesignInstanceLiveStateChoices.PENDING
                ),
                version=self.design_model().version,
            )
        instance.validated_save()

        journal = models.Journal(
            design_instance=instance,
            job_result=self.job_result,
        )
        journal.validated_save()
        return journal

    @staticmethod
    def validate_data_logic(data):
        """Method to validate the input data logic that is already valid as a form by the `validate_data` method."""

    def run(self, **kwargs):  # pylint: disable=arguments-differ
        """Render the design and implement it within a build Environment object."""
        try:
            return self._run_in_transaction(**kwargs)
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
    def _run_in_transaction(self, **kwargs):  # pylint: disable=too-many-branches
        """Render the design and implement it within a build Environment object.

        This version of `run` is wrapped in a transaction and will roll back database changes
        on error. In general, this method should only be called by the `run` method.
        """
        self.log_info(message=f"Building {getattr(self.Meta, 'name')}")
        extensions = getattr(self.Meta, "extensions", [])

        design_files = None

        if nautobot_version < "2.0.0":
            commit = kwargs["commit"]
            data = kwargs["data"]
        else:
            commit = kwargs.pop("dryrun", False)
            data = kwargs

        self.validate_data_logic(data)

        if nautobot_version < "2.0.0":
            self.job_result.job_kwargs = {"data": self.serialize_data(data)}
        else:
            self.job_result.job_kwargs = self.serialize_data(data)

        journal = self._setup_journal(data.pop("instance_name"))
        self.log_info(message=f"Building {getattr(self.Meta, 'name')}")
        extensions = getattr(self.Meta, "extensions", [])
        self.environment = Environment(
            job_result=self.job_result,
            extensions=extensions,
            journal=journal,
        )

        design_files = None

        if hasattr(self.Meta, "context_class"):
            context = self.Meta.context_class(data=data, job_result=self.job_result, design_name=self.Meta.name)
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
                self.post_implementation(context, self.environment)

                # The Journal stores the design (with Nautobot identifiers from post_implementation)
                # for future operations (e.g., updates)
                journal.builder_output = self.environment.builder_output
                journal.design_instance.status = Status.objects.get(
                    content_types=ContentType.objects.get_for_model(models.DesignInstance),
                    name=choices.DesignInstanceStatusChoices.ACTIVE,
                )
                journal.design_instance.save()
                journal.save()
                self.job_result.data["related_objects"] = {
                    "journal": journal.pk,
                    "design_instance": journal.design_instance.pk,
                }
                if hasattr(self.Meta, "report"):
                    self.report = self.render_report(context, self.environment.journal)
                    self.log_success(message=self.report)
                    if nautobot_version >= "2.0":
                        self.save_design_file("report.md", self.report)
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
            if nautobot_version >= "2":
                raise ex
        except Exception as ex:
            transaction.savepoint_rollback(sid)
            self.failed = True
            raise ex

    def save_design_file(self, filename, content):
        """Save some content to a job file.

        This is only supported on Nautobot 2.0 and greater.

        Args:
            filename (str): The name of the file to save.
            content (str): The content to save to the file.
        """
        if nautobot_version < "2.0":
            return

        FileProxy.objects.create(
            name=filename,
            job_result=self.job_result,
            file=ContentFile(content.encode("utf-8"), name=filename),
        )
