"""Extensions API for the object creator."""
import operator
import os
from abc import ABC
from functools import reduce
from typing import TYPE_CHECKING, Any
import netaddr

import yaml

from django.db.models import Q

from nautobot.ipam.models import Prefix

from design_builder import DesignBuilderConfig
from design_builder.errors import DesignImplementationError
from design_builder.git import GitRepo

if TYPE_CHECKING:
    from design import ModelInstance, Builder


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
        object_creator (ObjectCreator): The object creator that is implementing the
            current design.
    """

    def __init__(self, object_creator: "Builder"):  # noqa: D107
        self.object_creator = object_creator

    def attribute(self, value: Any, model_instance: "ModelInstance") -> None:
        """This method is called when the `attribute_tag` is encountered.

        Args:
            value (Any): The value of the data structure at this key's point in the design YAML. This could be a scalar, a dict or a list.
            model_instance (CreatorObject): Object is the CreatorObject that would ultimately contain the values.
        """

    def value(self, key: str) -> "ModelInstance":
        """Retrieve a CreatorObject to be assigned to the design.

        Args:
            key (str): The key to lookup the Creator Object.

        Returns:
            CreatorObject: A CreatorObject must be returned that will be used
            in place of the `!attribute_tag` placeholder.
        """

    def commit(self) -> None:
        """Optional method that is called once a design has been implemented and committed to the database."""
        # TODO: Need to write unit tests for this

    def roll_back(self) -> None:
        """Optional method that is called if the design has failed and the database transaction will be rolled back."""
        # TODO: Need to write unit tests for this


class ReferenceExtension(Extension):
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
        object_creator (ObjectCreator): The object creator that is implementing the
            current design.
    """

    attribute_tag = "ref"
    value_tag = "ref"

    def __init__(self, object_creator: "Builder"):  # noqa: D107
        super().__init__(object_creator)
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
        model_instance = self._env[key]
        if model_instance.instance:
            model_instance.instance.refresh_from_db()
        if attribute:
            return reduce(getattr, [model_instance.instance, *attribute.split(".")])
        return model_instance


class GitContextExtension(Extension):
    """Provides the "!git_context" attribute extension that will save content to a git repo.

    Args:
        object_creator (ObjectCreator): The object creator that is implementing the
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

    attribute_tag = "git_context"

    def __init__(self, object_creator: "Builder"):  # noqa: D107
        super().__init__(object_creator)
        self._env = {
            "files": [],
            "directories": [],
        }
        slug = DesignBuilderConfig.context_repository
        self.context_repo = GitRepo(slug, object_creator.job_result)

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
        required_fields = ["destination", "data"]
        for field in required_fields:
            if field not in value:
                raise DesignImplementationError(f"{field} is required for git_context")
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

    def roll_back(self):
        """Delete any files and directories that were created by the tag."""
        for file in self._env["files"]:
            os.remove(file)

        for dirpath in self._env["directories"]:
            os.rmdir(dirpath)


class NextPrefixExtension(Extension):
    """Provision the next prefix for a given set of parent prefixes."""

    attribute_tag = "next_prefix"

    def attribute(self, value: dict, creator_object) -> None:
        """Provides the `!next_prefix` attribute that will calculate the next available prefix.

        Args:
            value: A filter describing the parent prefix to provision from. If `prefix`
                is one of the query keys then the network and prefix length will be
                split and used as query arguments for the underlying Prefix object. The
                requested prefix length must be specified using the `length` dictionary
                key. All other keys are passed on to the query filter directly.


        Raises:
            DesignImplementationError: if value is not a dictionary, the prefix is improperly formatted
                or no query arguments were given. This error is also raised if the supplied parent
                prefixes are all full.

        Returns:
            The next available prefix of the requested size represented as a string.

        Example:
            ```yaml
            prefixes:
            - "!next_prefix":
                    prefix: "10.0.0.0/23,10.0.2.0/23"
                    length: 24
                status__name: "Active"
            ```
        """
        if not isinstance(value, dict):
            raise DesignImplementationError("the next_prefix tag requires a dictionary of arguments")

        length = value.pop("length", None)
        if length is None:
            raise DesignImplementationError("the next_prefix tag requires a prefix length")

        if len(value) == 0:
            raise DesignImplementationError("no search criteria specified for prefixes")

        query = Q(**value)
        if "prefix" in value:
            prefixes_str = value.pop("prefix")
            prefix_q = []
            for prefix_str in prefixes_str.split(","):
                prefix_str = prefix_str.strip()
                prefix = netaddr.IPNetwork(prefix_str)
                prefix_q.append(
                    Q(
                        prefix_length=prefix.prefixlen,
                        network=prefix.network,
                        broadcast=prefix.broadcast,
                    )
                )
            query = Q(**value) & reduce(operator.or_, prefix_q)

        prefixes = Prefix.objects.filter(query)
        return "prefix", self._get_next(prefixes, length)

    def _get_next(self, prefixes, length) -> str:  # pylint:disable=no-self-use
        """Return the next available prefix from a parent prefix.

        Args:
            prefixes (str): Comma separated list of prefixes to search for available subnets.
            length (int): The requested prefix length.

        Returns:
            str: The next available prefix
        """
        length = int(length)
        for requested_prefix in prefixes:
            for available_prefix in requested_prefix.get_available_prefixes().iter_cidrs():
                if available_prefix.prefixlen <= length:
                    return f"{available_prefix.network}/{length}"
        raise DesignImplementationError(f"No available prefixes could be found from {list(map(str, prefixes))}")
