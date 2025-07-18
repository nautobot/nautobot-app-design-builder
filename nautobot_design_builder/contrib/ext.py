"""Extra action tags that are not part of the core Design Builder."""

import operator
from functools import reduce
from typing import Any, Dict, Iterator, Tuple

import netaddr
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldError, MultipleObjectsReturned, ObjectDoesNotExist
from django.db.models import Q
from nautobot.circuits import models as circuits
from nautobot.dcim import models as dcim
from nautobot.ipam.models import Prefix

from nautobot_design_builder.design import Environment, ModelInstance, ModelMetadata
from nautobot_design_builder.errors import DesignImplementationError, DoesNotExistError, MultipleObjectsReturnedError
from nautobot_design_builder.ext import AttributeExtension
from nautobot_design_builder.jinja_filters import network_offset
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned


class LookupMixin:
    """A helper mixin that provides a way to lookup objects."""

    environment: Environment

    def lookup_by_content_type(self, app_label, model_name, query):
        """Perform a query on a model.

        Args:
            app_label: Content type app-label that the model exists in.

            model_name: Name of the model for the query.

            query: Dictionary to be used for the query.

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
            # pylint: disable=raise-missing-from
            raise DesignImplementationError(f"Could not find model class for {model_class}")

        return self.lookup(queryset, query)

    @staticmethod
    def _flatten(query: dict, prefix="") -> Iterator[Tuple[str, Any]]:
        """Perform the flattening of a query dictionary.

        Args:
            query (dict): The input query (or subquery during recursion) to flatten.

            prefix (str, optional): The prefix to add to each flattened key. Defaults to "".

        Returns:
            Iterator[Tuple[str, Any]]: A generator that yields they key/value pairs.
        """
        for key, value in query.items():
            if isinstance(value, dict):
                yield from LookupMixin._flatten(value, f"{prefix}{key}__")
            else:
                if isinstance(value, ModelInstance):
                    yield (f"!get:{prefix}{key}", value.design_instance)
                else:
                    yield (f"!get:{prefix}{key}", value)

    @staticmethod
    def flatten_query(query: dict) -> Dict[str, Any]:
        """Flatten a dictionary of dictionaries into query params.

        Django query arguments are a flat dictionary with the argument
        name being the query parameter and the value being what to match. However,
        it is sometimes clearer to express these queries in a hierarchy using dictionaries
        of dictionaries. The `_flatten` method will take this hierarchy and flatten
        it so that it can be expanded as keyword arguments for a Django query.

        Args:
            query (dict): The query dictionary to flatten.

        Returns:
            Dict[str, Any]: The flattened query dictionary.

        Example:
        ```python
        >>> query = {
        ...     "status": {
        ...         "name": "Active",
        ...     }
        ... }
        >>>
        >>> LookupMixin.flatten_query(query)
        {'status__name': 'Active'}
        >>>
        ```
        """
        return dict(LookupMixin._flatten(query))

    def lookup(self, queryset, query, parent: ModelInstance = None):
        """Perform a single object lookup from a queryset.

        Args:
            queryset: Queryset (e.g. Status.objects.all) from which to query.

            query: Query params to filter by.

            parent: Optional field used for better error reporting. Set this
                value to the model instance that is semantically the parent so
                that DesignModelErrors raised are more easily debugged.

        Raises:
            DoesNotExistError: If either no object is found.
            MultipleObjectsReturnedError: if multiple objects are found.

        Returns:
            Any: The object matching the query.
        """
        query = self.environment.resolve_values(query)
        # it's possible an extension actually returned the instance we need, in
        # that case, no need to look it up. This is especially true for the
        # !ref extension used as a value.
        if isinstance(query, ModelInstance):
            return query

        query = self.flatten_query(query)
        try:
            model_class = self.environment.model_class_index[queryset.model]
            if parent:
                return parent.design_metadata.create_child(model_class, query, queryset)
            return model_class(self.environment, query, queryset)
        except ObjectDoesNotExist:
            # pylint: disable=raise-missing-from
            raise DoesNotExistError(queryset.model, query_filter=query, parent=parent)
        except MultipleObjectsReturned:
            # pylint: disable=raise-missing-from
            raise MultipleObjectsReturnedError(queryset.model, query_filter=query, parent=parent)


class LookupExtension(AttributeExtension, LookupMixin):
    """Lookup a model instance and assign it to an attribute."""

    tag = "lookup"

    def attribute(self, *args, value, model_instance) -> None:  # pylint:disable=arguments-differ
        """Provides the `!lookup` attribute that will lookup an instance.

        This action tag can be used to lookup an object in the database and
        assign it to an attribute of another object.

        Args:
            *args: Any additional arguments following the tag name. These are `:` delimited.

            value: A filter describing the object to get. Keys should map to lookup
                parameters equivalent to Django's `filter()` syntax for the given model.
                The special `type` parameter will override the relationship's model class
                and instead lookup the model class using the `ContentType`. The value
                of the `type` field must match `ContentType` `app_label` and `model` fields.

            model_instance: The model instance that is the parent of this attribute lookup.

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


class CableConnectionExtension(AttributeExtension, LookupMixin):
    """Connect a cable termination to another cable termination."""

    tag = "connect_cable"

    @staticmethod
    def get_query_managers(endpoint_type):
        """Get the list of query managers for the `endpoint_type`.

        This method will return a list of query managers that correspond
        to types that can be connected to the `endpoint_type`. For instance,
        dcim.Interface types can be connected to dcim.FrontPort, dcim.RearPort,
        circuits.CircuitTermination or other dcim.Interface objects. If
        `dcim.Interface` is passed in, then the query manager for each of the
        other endpoint types is returned.

        Args:
            endpoint_type: Model class of the endpoint that is to be connected.

        Returns:
            list: A list of query managers for types that can be connected to.
        """
        interface_types = (dcim.FrontPort, dcim.RearPort, dcim.Interface, circuits.CircuitTermination)
        query_managers = None
        if issubclass(endpoint_type, interface_types):
            query_managers = [it.objects for it in interface_types]
        elif issubclass(endpoint_type, dcim.PowerPort):
            query_managers = [
                dcim.PowerFeed.objects,
                dcim.PowerOutlet.objects,
            ]
        elif issubclass(endpoint_type, dcim.PowerOutlet):
            query_managers = [dcim.PowerPort.objects]

        return query_managers

    def attribute(self, *args, value=None, model_instance: ModelInstance = None) -> None:
        """Connect a cable termination to another cable termination.

        Args:
            *args: Any additional arguments following the tag name. These are `:` delimited.

            value: Dictionary with details about the cable. At a minimum
                the dictionary must have a `to` key which includes a query
                dictionary that will return exactly one object to be added to the
                `termination_b` side of the cable. All other attributes map
                directly to the cable attributes. Cables require a status,
                so the `status` field is mandatory and follows typical design
                builder query lookup.

            model_instance: The object receiving the `a` side of this connection.

        Raises:
            DesignImplementationError: If no `status` was provided, or no matching
            termination was found.

        Returns:
            dict: All of the information needed to lookup or create a cable instance.

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
                    to:
                        device: "!ref:device1"
                        name: "GigabitEthernet1"
            ```
        """
        if "to" not in value:
            raise DesignImplementationError(
                f"`connect_cable` must have a `to` field indicating what to terminate to. {value}"
            )

        cable_attributes = {**value}
        termination_query = cable_attributes.pop("to")
        remote_instance = None
        query_managers = self.get_query_managers(model_instance.model_class)
        while remote_instance is None:
            try:
                remote_instance = self.lookup(query_managers.pop(0), termination_query)
            except (DoesNotExistError, FieldError):
                if not query_managers:
                    # pylint:disable=raise-missing-from
                    raise DoesNotExistError(
                        model=model_instance.model_class, parent=model_instance, query_filter=termination_query
                    )

        def connect():
            cable_attributes.update(
                {
                    "!create_or_update:termination_a_id": model_instance.design_instance.id,
                    "!create_or_update:termination_a_type_id": ContentType.objects.get_for_model(
                        model_instance.design_instance
                    ).id,
                    "!create_or_update:termination_b_id": remote_instance.design_instance.id,
                    "!create_or_update:termination_b_type_id": ContentType.objects.get_for_model(
                        remote_instance.design_instance
                    ).id,
                }
            )

            existing_cable = dcim.Cable.objects.filter(
                Q(termination_a_id=model_instance.design_instance.id)
                | Q(termination_b_id=remote_instance.design_instance.id)
            ).first()
            Cable = self.environment.model_factory(dcim.Cable)  # pylint:disable=invalid-name
            if existing_cable:
                if (
                    existing_cable.termination_a_id != model_instance.design_instance.id
                    or existing_cable.termination_b_id != remote_instance.design_instance.id
                ):
                    self.environment.decommission_object(existing_cable.id, f"Cable {existing_cable.id}")
            cable = Cable(self.environment, cable_attributes)
            cable.save()

        model_instance.connect("POST_INSTANCE_SAVE", connect)


class NextPrefixExtension(AttributeExtension):
    """Provision the next prefix for a given set of parent prefixes."""

    tag = "next_prefix"

    def attribute(self, *args, value: dict = None, model_instance: ModelInstance = None) -> None:
        """Provides the `!next_prefix` attribute that will calculate the next available prefix.

        Args:
            *args: Any additional arguments following the tag name. These are `:` delimited.

            value: A filter describing the parent prefix to provision from. If `prefix`
                is one of the query keys then the network and prefix length will be
                split and used as query arguments for the underlying Prefix object. The
                requested prefix length must be specified using the `length` dictionary
                key. All other keys are passed on to the query filter directly.

            model_instance: The prefix object that will ultimately be saved to the database.

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
                    prefix:
                    - "10.0.0.0/23"
                    - "10.0.2.0/23"
                    length: 24
                    identified_by:
                        tag__name: "some tag name"
                status__name: "Active"
            ```
        """
        if not isinstance(value, dict):
            raise DesignImplementationError("the next_prefix tag requires a dictionary of arguments")
        identified_by = value.pop("identified_by", None)
        if identified_by:
            try:
                model_instance.design_instance = model_instance.relationship_manager.get(**identified_by)
                return None
            except ObjectDoesNotExist:
                pass
        length = value.pop("length", None)
        if length is None:
            raise DesignImplementationError("the next_prefix tag requires a prefix length")

        if len(value) == 0:
            raise DesignImplementationError("no search criteria specified for prefixes")

        query = Q(**value)
        if "prefix" in value:
            prefixes = value.pop("prefix")
            prefix_q = []
            if isinstance(prefixes, str):
                prefixes = [prefixes]
            elif not isinstance(prefixes, list):
                raise DesignImplementationError("Prefixes should be a string (single prefix) or a list.")

            for prefix_str in prefixes:
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
        attr = args[0] if args else "prefix"
        return attr, self._get_next(prefixes, length)

    @staticmethod
    def _get_next(prefixes, length) -> str:
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


class ChildPrefixExtension(AttributeExtension):
    """Calculates a child Prefix string in CIDR notation."""

    tag = "child_prefix"

    def attribute(self, *args, value: dict = None, model_instance: "ModelInstance" = None) -> None:
        """Provides the `!child_prefix` attribute.

        !child_prefix calculates a child prefix using a parent prefix
        and an offset. The parent prefix can either be a string CIDR
        style prefix or it can refer to a previously created `Prefix`
        object.

        Args:
            *args: Any additional arguments following the tag name. These are `:` delimited.

            value: a dictionary containing the `parent` prefix (string or
                `Prefix` instance) and the `offset` in the form of a CIDR
                string. The length of the child prefix will match the length
                provided in the offset string.

            model_instance: The object that this prefix string should be assigned to.
                It could be an IP Address or Prefix or any field that takes a
                dotted decimal address string.

        Raises:
            DesignImplementationError: if value is not a dictionary, or the
            prefix or offset are improperly formatted

        Returns:
            The computed prefix string.

        Example:
            ```yaml
            prefixes:
            - "!next_prefix":
                    prefix:
                    - "10.0.0.0/23"
                    length: 24
                status__name: "Active"
                "!ref": "parent_prefix"
            - "!child_prefix":
                    parent: "!ref:parent_prefix"
                    offset: "0.0.0.0/25"
                status__name: "Active"
            - "!child_prefix":
                    parent: "!ref:parent_prefix"
                    offset: "0.0.0.128/25"
                status__name: "Active"
            ```
        """
        if not isinstance(value, dict):
            raise DesignImplementationError("the child_prefix tag requires a dictionary of arguments")

        action = value.pop("action", "")

        parent = value.pop("parent", None)
        if parent is None:
            raise DesignImplementationError("the child_prefix tag requires a parent")
        if isinstance(parent, ModelInstance):
            parent = str(parent.design_instance.prefix)
        elif not isinstance(parent, str):
            raise DesignImplementationError("parent prefix must be either a previously created object or a string.")

        offset = value.pop("offset", None)
        if offset is None:
            raise DesignImplementationError("the child_prefix tag requires an offset")
        if not isinstance(offset, str):
            raise DesignImplementationError("offset must be string")
        attr = args[0] if args else "prefix"

        if action:
            model_instance.design_metadata.action = action
            model_instance.design_metadata.filter[attr] = str(network_offset(parent, offset))
            return None
        return attr, str(network_offset(parent, offset))


class BGPPeeringExtension(AttributeExtension):
    """
    Extension to create and manage BGP Peerings with peer_groups using nautobot-app-bgp-models.

    Usage in YAML:
      - "!bgp_peering":
          endpoint_a:
            routing_instance: "!ref:rr1_65000_ri"
            source_interface: "!ref:rr1_loopback0"
            source_ip: "!ref:rr1_loopback0_ipv4"
            peer_group: "!ref:backbone_rr_ipv4_peers_pg"
            description: rr1_loopback0
          endpoint_z:
            routing_instance: "!ref:p1_65000_ri"
            source_interface: "!ref:p1_loopback0"
            source_ip: "!ref:p1_loopback0_ipv4"
            peer_group: "!ref:backbone_rr_ipv4_peers_pg"
            description: p1_loopback0
          status__name: "Active"

    Without Peer_Groups
    - "!bgp_peering":
        endpoints:
        - routing_instance: "!ref:rr1_65000_ri"
          source_interface: "!ref:rr1_loopback0"
          source_ip: "!ref:rr1_loopback0_ipv4"
          afi_safis:
          - ipv4_unicast
          description: rr1_loopback0
        - routing_instance: "!ref:p1_65000_ri"
          source_interface: "!ref:p1_loopback0"
          source_ip: "!ref:p1_loopback0_ipv4"
          afi_safis:
          - ipv4_unicast
          description: p1_loopback0
        status__name: "Active"
    """

    tag = "bgp_peering"

    def __init__(self, environment: Environment):
        super().__init__(environment)
        try:
            from nautobot_bgp_models.models import (
                PeerEndpoint,
                Peering,
                PeerGroup,
                BGPRoutingInstance,
            )
            from nautobot.dcim.models import Interface
            from nautobot.ipam.models import IPAddress

            self.PeerEndpoint = self.environment.model_factory(PeerEndpoint)
            self.Peering = self.environment.model_factory(Peering)
            self.PeerGroup = self.environment.model_factory(PeerGroup)
            self.RoutingInstance = self.environment.model_factory(BGPRoutingInstance)
            self.Interface = self.environment.model_factory(Interface)
            self.IPAddress = self.environment.model_factory(IPAddress)
        except ModuleNotFoundError:
            raise DesignImplementationError(
                "the `bgp_peering` tag can only be used when the bgp models app is installed."
            )

    def resolve_or_create(self, model_factory, filters):
        """Look up or create a model instance by !ref, ModelInstance, or filters dict."""
        if isinstance(filters, ModelInstance):
            return filters
        if isinstance(filters, str) and filters.startswith("!ref:"):
            return filters
        if isinstance(filters, dict):
            try:
                return model_factory(self.environment, filters)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                raise DesignImplementationError(
                    f"Could not find or resolve {model_factory.model_class.__name__} with filters: {filters}"
                )
        raise DesignImplementationError(
            f"Invalid type for {model_factory.model_class.__name__}: {type(filters)}"
        )

    def build_peer_endpoint(self, endpoint_data):
        """Build or look up a PeerEndpoint using !refs, ModelInstances, or filters."""
        endpoint = dict(endpoint_data)

        if "routing_instance" in endpoint:
            endpoint["routing_instance"] = self.resolve_or_create(self.RoutingInstance, endpoint["routing_instance"])
        elif any(k.startswith("routing_instance__") for k in endpoint.keys()):
            ri_filter = {k.replace("routing_instance__", ""): endpoint.pop(k) for k in list(endpoint) if k.startswith("routing_instance__")}
            endpoint["routing_instance"] = self.resolve_or_create(self.RoutingInstance, ri_filter)
        else:
            raise DesignImplementationError("Missing routing_instance in PeerEndpoint definition.")

        if "peer_group" in endpoint:
            endpoint["peer_group"] = self.resolve_or_create(self.PeerGroup, endpoint["peer_group"])
        elif "peer_group__name" in endpoint:
            ri = endpoint["routing_instance"]
            endpoint["peer_group"] = self.resolve_or_create(
                self.PeerGroup,
                {
                    "name": endpoint.pop("peer_group__name"),
                    "routing_instance": ri,
                },
            )

        if "source_interface" in endpoint:
            endpoint["source_interface"] = self.resolve_or_create(
                self.Interface,
                endpoint["source_interface"],
            )

        if "source_ip" in endpoint:
            endpoint["source_ip"] = self.resolve_or_create(
                self.IPAddress,
                endpoint["source_ip"],
            )

        # Always set description if not already defined
        if "description" not in endpoint:
            dev = endpoint["routing_instance"].design_instance.device.name
            intf = endpoint["source_interface"].design_instance.name
            endpoint["description"] = f"{dev}_{intf}"

        return self.PeerEndpoint(self.environment, endpoint)

    def attribute(self, *args, value=None, model_instance: ModelInstance = None):
        """
        Create a Peering with two PeerEndpoints, peer groups, source interfaces, and addresses.
        Accepts:
        - endpoint_a/endpoint_z keys (legacy)
        - endpoints: [ endpoint_a_dict, endpoint_z_dict ] (preferred, modern)
        """
        if (
            not isinstance(value, dict) or
            not (
                (("endpoint_a" in value and "endpoint_z" in value) or
                ("endpoints" in value and isinstance(value["endpoints"], list) and len(value["endpoints"]) == 2))
            )
        ):
            raise DesignImplementationError("bgp_peering requires either endpoint_a and endpoint_z keys or an endpoints list of length 2")

        if "endpoints" in value:
            endpoint_a_data, endpoint_z_data = value["endpoints"]
        else:
            endpoint_a_data = value["endpoint_a"]
            endpoint_z_data = value["endpoint_z"]

        endpoint_a = self.build_peer_endpoint(endpoint_a_data)
        endpoint_z = self.build_peer_endpoint(endpoint_z_data)

        peering_a = getattr(endpoint_a.design_instance, "peering", None)
        peering_z = getattr(endpoint_z.design_instance, "peering", None)
        retval = {**value}

        if peering_a == peering_z:
            if peering_a:
                retval["!update:pk"] = peering_a.pk
        else:
            if peering_a:
                peering_a.delete()
            if peering_z:
                peering_z.delete()

        retval["endpoints"] = [endpoint_a, endpoint_z]
        endpoint_a.design_metadata.attributes["peering"] = model_instance
        endpoint_z.design_metadata.attributes["peering"] = model_instance

        def post_save():
            peering_instance: ModelInstance = model_instance
            endpoint_a = peering_instance.design_instance.endpoint_a
            endpoint_z = peering_instance.design_instance.endpoint_z
            endpoint_a.peer, endpoint_z.peer = endpoint_z, endpoint_a
            endpoint_a.save()
            endpoint_z.save()

        model_instance.connect(ModelMetadata.POST_SAVE, post_save)
        return retval