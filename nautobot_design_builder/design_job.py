"""Base Design Job class definition."""
import sys
import itertools
import copy
import traceback
from abc import ABC, abstractmethod
from os import path
from datetime import datetime
import yaml
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

from jinja2 import TemplateError

from nautobot.extras.models import Status
from nautobot.extras.jobs import Job, StringVar


from nautobot_design_builder.errors import DesignImplementationError, DesignModelError
from nautobot_design_builder.jinja2 import new_template_environment
from nautobot_design_builder.logging import LoggingMixin
from nautobot_design_builder.design import Builder
from nautobot_design_builder.context import Context
from nautobot_design_builder import models
from nautobot_design_builder import choices
from nautobot_design_builder.constants import NAUTOBOT_ID

from .util import nautobot_version


class DesignJob(Job, ABC, LoggingMixin):  # pylint: disable=too-many-instance-attributes
    """The base Design Job class that all specific Design Builder jobs inherit from.

    DesignJob is an abstract base class that all design implementations must implement.
    Any design that is to be included in the list of Jobs in Nautobot *must* include
    a Meta class.
    """

    instance_name = StringVar(label="Instance Name", max_length=models.DESIGN_NAME_MAX_LENGTH)
    owner = StringVar(label="Implementation Owner", required=False, max_length=models.DESIGN_OWNER_MAX_LENGTH)

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

    def design_model(self):
        """Get the related Job."""
        return models.Design.objects.for_design_job(self.job_result.job_model)

    def post_implementation(self, context: Context, builder: Builder):
        """Similar to Nautobot job's `post_run` method, but will be called after a design is implemented.

        Any design job that requires additional work to be completed after the design
        has been implemented can provide a `post_implementation` method. This method will be
        called after the entire set of design files has been implemented and the database
        transaction has been committed.

        Args:
            context (Context): The render context that was used for rendering the
            design files.

            builder (Builder): The builder object that consumed the rendered design
            files. This is useful for accessing the design journal.
        """

    def post_run(self):
        """Method that will run after the main Nautobot job has executed."""
        if self.rendered:
            self.job_result.data["output"] = self.rendered

        self.job_result.data["designs"] = self.designs

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

        def update_design_items(new_value, old_value):
            """Recursive function to adapt the new design taken into account the previous one."""
            if isinstance(new_value, list):
                elements_to_be_deleted = []

                for elem1, elem2 in itertools.zip_longest(new_value, old_value):
                    if elem1 is None:
                        # FIXME: If there are more elements in the old list, these should be deleted
                        print("element to be deleted")
                        if isinstance(elem2, dict):
                            elem2["!delete:"] = {NAUTOBOT_ID: elem2[NAUTOBOT_ID]}
                            elements_to_be_deleted.append(elem2)
                    elif elem2 is None:
                        # If it is a new element in the design, we pass it as it is, no previous reference to be taken into account.
                        pass
                    elif isinstance(elem1, dict) and isinstance(elem2, dict):
                        update_design_items(elem1, elem2)
                    else:
                        raise DesignImplementationError("Unexpected type of object.")

                new_value.extend(elements_to_be_deleted)

            elif isinstance(new_value, dict):
                for inner_old_key in old_value:
                    # Reseting desired values for attributes not included in the new design implementation
                    # TODO: use well-know references and  rethink this approach to cover more cases
                    if inner_old_key not in new_value and inner_old_key != NAUTOBOT_ID and "!" not in inner_old_key:
                        new_value[inner_old_key] = None

                for inner_key, inner_value in new_value.copy().items():
                    if inner_key in old_value and new_value[inner_key] == old_value[inner_key] and "!" not in inner_key:
                        # If the values of the attribute in the design are the same, remove it for simplification
                        del new_value[inner_key]
                        continue

                    if isinstance(inner_value, dict) or isinstance(inner_value, list):
                        # If an attribute is a dict or list, explore it recursively
                        # TODO: check how this works with config context
                        update_design_items(inner_value, old_value[inner_key])

                if NAUTOBOT_ID in old_value:
                    new_value[NAUTOBOT_ID] = old_value[NAUTOBOT_ID]

        design = self.render_design(context, design_file)

        # The design to apply will take into account the previous journal that keeps track (in the builder_output)
        # of the design used (i.e., the YAML) including the Nautobot IDs that will help to reference them
        self.builder.builder_output[design_file] = copy.deepcopy(design)

        last_journal = (
            self.builder.journal.design_journal.design_instance.journals.filter(active=True)
            .exclude(id=self.builder.journal.design_journal.id)
            .last()
        )
        if last_journal:
            if not last_journal.builder_output:
                # TODO: manage this case? In normal situation this should not ever happen
                return

            # The last design output is used as the reference to understand what needs to be changed
            # The design output store the whole set of attributes, not only the ones taken into account
            # in the implementation
            previous_design = last_journal.builder_output[design_file]
            for key, value in design.items():
                old_value = previous_design[key]
                update_design_items(value, old_value)

        self.builder.implement_design(design, commit, design_file)

    def _setup_journal(self, instance_name: str, design_owner: str):
        try:
            instance = models.DesignInstance.objects.get(name=instance_name)
            self.log_info(message=f'Existing design instance of "{instance_name}" was found, re-running design job.')
            instance.last_implemented = datetime.now()
        except models.DesignInstance.DoesNotExist:
            self.log_info(message=f'Implementing new design "{instance_name}".')
            content_type = ContentType.objects.get_for_model(models.DesignInstance)
            instance = models.DesignInstance(
                name=instance_name,
                owner=design_owner,
                design=self.design_model(),
                last_implemented=datetime.now(),
                status=Status.objects.get(content_types=content_type, name=choices.DesignInstanceStatusChoices.ACTIVE),
                live_state=Status.objects.get(
                    content_types=content_type, name=choices.DesignInstanceLiveStateChoices.PENDING
                ),
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

    @transaction.atomic
    def run(self, **kwargs):  # pylint: disable=arguments-differ,too-many-branches
        """Render the design and implement it with a Builder object."""
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

        journal = self._setup_journal(data.pop("instance_name"), data.pop("owner"))
        self.log_info(message=f"Building {getattr(self.Meta, 'name')}")
        extensions = getattr(self.Meta, "extensions", [])
        self.builder = Builder(
            job_result=self.job_result,
            extensions=extensions,
            journal=journal,
        )

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
                self.post_implementation(context, self.builder)

                # The Journal stores the design YAMLs (with IDs) for future operations (e.g., updates)
                journal.builder_output = self.builder.builder_output

                journal.design_instance.status = Status.objects.get(
                    content_types=ContentType.objects.get_for_model(models.DesignInstance),
                    name=choices.DesignInstanceStatusChoices.ACTIVE,
                )
                journal.design_instance.save()
                journal.save()
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
