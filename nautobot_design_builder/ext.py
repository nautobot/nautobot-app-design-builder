"""Extensions API for the object creator."""
import os
from abc import ABC, abstractmethod
from functools import reduce
from typing import TYPE_CHECKING, Any, List

import inspect
import sys
from types import ModuleType
import yaml

from nautobot_design_builder import NautobotDesignBuilderConfig
from nautobot_design_builder.errors import DesignImplementationError
from nautobot_design_builder.git import GitRepo

if TYPE_CHECKING:
    from design import ModelInstance, Builder


def is_extension(cls):
    """Determine if a class is an Extension."""
    return inspect.isclass(cls) and issubclass(cls, Extension) and cls is not Extension


def extensions(module: ModuleType = None) -> List["Extension"]:
    """Get all the extensions defined in a module.

    Args:
        module (ModuleType): Module to search for extensions. If left as `None` then the ext.py module is searched.

    Returns:
        List[Extension]: List of extensions found in the module.
    """
    if module is None:
        module = sys.modules[__name__]

    def matches(value):
        if hasattr(value, "__module__"):
            if value.__module__ == module.__name__:
                return is_extension(value)
        return False

    return [extension[1] for extension in inspect.getmembers(module, matches)]


class Extension(ABC):
    """Base class for attribute and value extensions.

    Extensions add capabilities to the object creator. For instance,
    the ReferenceExtension provides both the `!ref` attribute (which
    saves references to ORM objects) as well as the `!ref` value lookup
    that returns previously saved references.

    To develop a new extension, simply extend this base class and provide
    ether an `attribute` or `value` to be handled by the extension. For
    `attribute` extensions, a class variable named `attribute_tag` must
    be provided to indicate the tag name (such as "ref" for the `!ref` tag). A
    corresponding instance method named `attribute` must also be provided.

    Likewise, for a value extension the `value_tag` and `value` instance
    method must be provided.

    The `__init__` method is called only once. The extension is initialized when the first
    tag matching `tag_name` or `value_name` is encountered.

    Args:
        builder (Builder): The object creator that is implementing the
            current design.
    """

    @property
    @abstractmethod
    def tag(self):
        """All Extensions must specify their tag name.

        The `tag` method indicates to the Builder what the
        tag name is for this extensions. For instance, a `tag`
        of `ref` will match `!ref` in the design.
        """

    def __init__(self, builder: "Builder"):  # noqa: D107
        self.builder = builder

    def commit(self) -> None:
        """Optional method that is called once a design has been implemented and committed to the database.

        Note: Commit is called once for each time Builder.implement_design is called. For a design job with
        multiple design files, commit will be called once for each design file. It is up to the extension
        to track internal state so that multiple calls to `commit` don't introduce an inconsistency.
        """

    def roll_back(self) -> None:
        """Optional method that is called if the design has failed and the database transaction will be rolled back."""


class AttributeExtension(Extension, ABC):
    """An `AttributeExtension` will be evaluated when the design key matches the `tag`."""

    @abstractmethod
    def attribute(self, value: Any, model_instance: "ModelInstance") -> None:
        """This method is called when the `attribute_tag` is encountered.

        Args:
            value (Any): The value of the data structure at this key's point in the design YAML. This could be a scalar, a dict or a list.
            model_instance (CreatorObject): Object is the CreatorObject that would ultimately contain the values.
        """


class ValueExtension(Extension, ABC):
    """A `ValueExtension` will be matched when a design value matches the `tag`."""

    @abstractmethod
    def value(self, key: str) -> "ModelInstance":
        """Retrieve a CreatorObject to be assigned to the design.

        Args:
            key (str): The key to lookup the Creator Object.

        Returns:
            CreatorObject: A CreatorObject must be returned that will be used
            in place of the `!attribute_tag` placeholder.
        """


class ReferenceExtension(AttributeExtension, ValueExtension):
    """An ObjectCreator extension the creates references to objects and retrieves them.

    This extension is both an attribute extension and a value extension that is
    associated with the `ref` tag in both cases. When using this extension as an attribute,
    the value should be a string representing the name of the reference to be used later. The name
    of the reference must not include any dots, as dotted notation in the reference lookup indicates that
    the model attribute should be returned rather than the model itself.

    When used as a value extension, the syntax is `!ref:name_previously_used` where
    `name_previously_used` matches the string value provided to the original `!ref` attribute. With
    only the reference name, the entire CreatorObject is returned for assignment, when the name is
    followed by a dot and an attribute name, then only that matching attribute is returned from the
    stored creator object.

    Args:
        builder (Builder): The object creator that is implementing the
            current design.
    """

    tag = "ref"

    def __init__(self, builder: "Builder"):  # noqa: D107
        super().__init__(builder)
        self._env = {}

    def attribute(self, value, model_instance):
        """This method is called when the `!ref` tag is encountered.

        Args:
            value (Any): Value should be a string name (the reference) to refer to the object
            model_instance (CreatorObject): The object that will be later referenced

        Example:
            ```yaml
            devices:
                - name: "My Device"
                  "!ref": "my_device"
            ```

            The `ReferenceExtension.attribute` method is called when the `!ref` attribute
            is encountered. The `value` argument of the method will be the string `my_device` and
            the `object` argument will be set to a `CreatorObject` containing the "My Device"
            `dcim.models.Device` instance that is being created. If the value is a list, then
            one reference will be created for each of the items in the list.
        """
        if isinstance(value, list):
            for item in value:
                self._env[item] = model_instance
        else:
            self._env[value] = model_instance

    def value(self, key) -> "ModelInstance":
        """Return the CreatorObject that is stored at `key`.

        Args:
            key (str): The reference name

        Returns:
            CreatorObject: The object stored at `reference_name`
        """
        keys = key.split(".", 1)
        attribute = None
        if len(keys) == 2:
            key, attribute = keys
        try:
            model_instance = self._env[key]
        except KeyError:
            # pylint: disable=raise-missing-from
            raise DesignImplementationError(f"No ref named {key} has been saved in the design.")
        if model_instance.instance and not model_instance.instance._state.adding:  # pylint: disable=protected-access
            model_instance.instance.refresh_from_db()
        if attribute:
            return reduce(getattr, [model_instance.instance, *attribute.split(".")])
        return model_instance


class GitContextExtension(AttributeExtension):
    """Provides the "!git_context" attribute extension that will save content to a git repo.

    Args:
        builder (Builder): The object creator that is implementing the
            current design.

    Example:
        ```yaml
        devices:
            - name: "My Device"
                "!git_context":
                destination: "config/my_device.yml"
                data:
                    bgp_asn: 64495
        ```

        The above will implement the design and when the `!git_context` tag is encountered
        it will marshal the dictionary at `data` to `config/my_device.yml` to the base directory
        of the git repository. TODO: explain how the git repo is configured. Potentially change
        the configuration to have git_slug directly in the tag content?
    """

    tag = "git_context"

    def __init__(self, builder: "Builder"):  # noqa: D107
        super().__init__(builder)
        slug = NautobotDesignBuilderConfig.context_repository
        self.context_repo = GitRepo(slug, builder.job_result)
        self._env = {}
        self._reset()

    def _reset(self):
        """Reset the internal state for commit/rollback tracking."""
        self._env = {
            "files": [],
            "directories": [],
        }

    def attribute(self, value, model_instance):
        """Provide the attribute tag functionality for git_context.

        Args:
            value (Any): Value should be a dictionary with the required fields `destination` and
                `data`. The `destination` field of the dictionary indicates the relative path to
                store information in the git repo. The `data` field contains the information that
                should be written to the git repository.
            model_instance (CreatorObject): The object containing the data.

        Raises:
            DesignImplementationError: raised if a required field is missing from the attribute's dictionary.
        """
        required_fields = set("destination", "data")
        missing_fields = required_fields - set(value.keys())
        if missing_fields:
            missing_fields = ", ".join(missing_fields)
            raise DesignImplementationError(f"git-context is missing {missing_fields}")

        base_dir = self.context_repo.path
        output_dir = os.path.join(base_dir, os.path.dirname(value["destination"]))
        try:
            os.makedirs(output_dir)
            self._env["directories"].append(output_dir)
        except FileExistsError:
            # this just means the directory exists
            # prior to this particular change, so don't
            # record that the directory was created so we
            # don't accidentally remove it during roll back
            pass

        output_file = os.path.join(base_dir, value["destination"])
        with open(output_file, "w", encoding="UTF-8") as context_file:
            yaml.dump(value["data"], context_file)
        self._env["files"].append(output_file)

    def commit(self):
        """Commit the added files to the git repository and push the changes."""
        self.context_repo.commit_with_added("Created by design builder")
        self.context_repo.push()
        self._reset()

    def roll_back(self):
        """Delete any files and directories that were created by the tag."""
        for file in self._env["files"]:
            os.remove(file)

        for dirpath in self._env["directories"]:
            os.rmdir(dirpath)
        self._reset()
