"""Extra action tags that are not part of the core Design Builder."""
from functools import reduce
import operator

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Q

from nautobot.dcim.models import Cable
from nautobot.extras.models import Status
from nautobot.ipam.models import Prefix

import netaddr

from design_builder.errors import DesignImplementationError
from design_builder.ext import Extension


class LookupMixin:
    """A helper mixin that provides a way to lookup objects."""

    def lookup_by_content_type(self, app_label, model_name, query):
        """Perform a query on a model.

        Args:
            app_label: Content type app-label that the model exists in.
            model_name_: Name of the model for the query.
            query (_type_): Dictionary to be used for the query.

        Raises:
            DesignImplementationError: If no matching object is found or no
            matching content-type is found.

        Returns:
            Any: The object matching the query.
        """
        try:
            content_type = ContentType.objects.get_by_natural_key(app_label, model_name)
            model_class = content_type.model_class()
            queryset = model_class.objects
        except ContentType.DoesNotExist:
            raise DesignImplementationError(f"Could not find model class for {model_class}")

        return self.lookup(queryset, query)

    def lookup(self, queryset, query):  # pylint: disable=R0201
        """Perform a single object lookup from a queryset.

        Args:
            queryset: Queryset (e.g. Status.objects.all) from which to query.
            query: Query params to filter by.

        Raises:
            DesignImplementationError: If either no object is found, or multiple objects are found.

        Returns:
            Any: The object matching the query.
        """
        for key, value in query.items():
            if hasattr(value, "instance"):
                query[key] = value.instance
        try:
            return queryset.get(**query)
        except ObjectDoesNotExist:
            raise DesignImplementationError(f"no {queryset.model.__name__} matching {query}")
        except MultipleObjectsReturned:
            raise DesignImplementationError(f"Multiple {queryset.model.__name__} objects match {query}")


class LookupExtension(Extension, LookupMixin):
    """Lookup a model instance and assign it to an attribute."""

    attribute_tag = "lookup"

    def attribute(self, *args, value, model_instance) -> None:  # pylint:disable=arguments-differ
        """Provides the `!lookup` attribute that will lookup an instance.

        This action tag can be used to lookup an object in the database and
        assign it to an attribute of another object.

        Args:
            value: A filter describing the object to get. Keys should map to lookup
            parameters equivalent to Django's `filter()` syntax for the given model.
            The special `type` parameter will override the relationship's model class
            and instead lookup the model class using the `ContentType`. The value
            of the `type` field must match `ContentType` `app_label` and `model` fields.

        Raises:
            DesignImplementationError: if no matching object was found.

        Returns:
            The attribute name and found object.

        Example:
            ```yaml
            cables:
            - "!lookup:termination_a":
                    content-type: "dcim.interface"
                    device__name: "device1"
                    name: "Ethernet1/1"
              "!lookup:termination_b":
                    content-type: "dcim.interface"
                    device__name: "device2"
                    name: "Ethernet1/1"
            ```
        """
        if len(args) < 1:
            raise DesignImplementationError('No attribute given for the "!lookup" tag.')

        attribute = args[0]
        query = {}
        if isinstance(value, str):
            if len(args) < 2:
                raise DesignImplementationError("No query attribute was given")
            query = {args[1]: value}
        elif isinstance(value, dict):
            query = value
        else:
            raise DesignImplementationError("the lookup requires a query attribute and value or a query dictionary.")

        content_type = query.pop("content-type", None)
        if content_type is None:
            descriptor = getattr(model_instance.model_class, attribute)
            model_class = descriptor.field.related_model
            app_label = model_class._meta.app_label
            model_name = model_class._meta.model_name
        else:
            app_label, model_name = content_type.split(".")

        return attribute, self.lookup_by_content_type(app_label, model_name, query)


class CableConnectionExtension(Extension, LookupMixin):
    """Connect a cable termination to another cable termination."""

    attribute_tag = "connect_cable"

    def attribute(self, value, model_instance) -> None:
        """Connect a cable termination to another cable termination.

        Args:
            value: Query for the `termination_b` side. This dictionary must
            include a field `status` or `status__<lookup param>` that is either
            a reference to a status object (former) or a lookup key/value to
            get a status (latter). The query must also include enough
            differentiating lookup params to retrieve a single matching termination
            of the same type as the `termination_a` side.

        Raises:
            DesignImplementationError: If no `status` was provided, or no matching
            termination was found.

        Returns:
            None: This tag does not return a value, as it adds a deferred object
            representing the cable connection.

        Example:
            ```yaml
            devices:
            - name: "Device 2"
              site__name: "Site"
              status__name: "Active"
              device_role__name: "test-role"
              device_type__model: "test-type"
              interfaces:
                - name: "GigabitEthernet1"
                  type: "1000base-t"
                  status__name: "Active"
                  "!connect_cable":
                    status__name: "Planned"
                    device: "!ref:device1"
                    name: "GigabitEthernet1"
            ```
        """
        query = {**value}
        status = query.pop("status", None)
        if status is None:
            for key in list(query.keys()):
                if key.startswith("status__"):
                    status_lookup = key[len("status__") :]  # noqa: E203
                    status = Status.objects.get(**{status_lookup: query.pop(key)})
                    break
        elif isinstance(status, dict):
            status = Status.objects.get(**status)
        elif hasattr(status, "instance"):
            status = status.instance

        if status is None:
            raise DesignImplementationError("No status given for cable connection")

        remote_instance = self.lookup(model_instance.model_class.objects, query)
        model_instance.deferred.append("cable")
        model_instance.deferred_attributes["cable"] = [
            model_instance.__class__(
                self.object_creator,
                model_class=Cable,
                attributes={
                    "status": status,
                    "termination_a": model_instance,
                    "termination_b": remote_instance,
                },
            )
        ]


class NextPrefixExtension(Extension):
    """Provision the next prefix for a given set of parent prefixes."""

    attribute_tag = "next_prefix"

    def attribute(self, value: dict, model_instance) -> None:
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
