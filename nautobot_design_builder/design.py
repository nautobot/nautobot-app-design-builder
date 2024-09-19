"""Provides ORM interaction for design builder."""

from types import FunctionType
from typing import Any, Dict, List, Mapping, Type, Union

from django.apps import apps
from django.db.models import Model, Manager, QuerySet
from django.db.models.fields import Field as DjangoField
from django.core.exceptions import ObjectDoesNotExist, ValidationError, MultipleObjectsReturned


from nautobot.core.graphql.utils import str_to_var_name
from nautobot.extras.models import JobResult, Relationship

from nautobot_design_builder import errors
from nautobot_design_builder import ext
from nautobot_design_builder.logging import LoggingMixin
from nautobot_design_builder.fields import CustomRelationshipField, field_factory


class Journal:
    """Keep track of the objects created or updated during the course of a design's implementation.

    The Journal provides a way to do post-implementation processing. For
    instance, if every item created in a design needs to be updated with
    a tag, then a post_implementation method can be created in the
    job and the journal.created items can be iterated and updated. The
    Journal contains three indices:

    index: a set of all the model UUIDs that have been created or updated

    created: a dictionary of objects created. The keys of this index are
    model classes and the values are sets of primary key UUIDs

    updated: like created, this index is a dictionary of objects that
    have been updated. The keys are model classes and the values are the primary
    key UUIDs

    An object's UUID may appear in both created and updated. However, they
    will only be in each of those indices at most once.
    """

    def __init__(self):
        """Constructor for Journal object."""
        self.index = set()
        self.created = {}
        self.updated = {}

    def log(self, model: "ModelInstance"):
        """Log that a model has been created or updated.

        Args:
            model (BaseModel): The model that has been created or updated
        """
        instance = model.instance
        model_type = instance.__class__
        if instance.pk not in self.index:
            self.index.add(instance.pk)

            if model.metadata.created:
                index = self.created
            else:
                index = self.updated

            index.setdefault(model_type, set())
            index[model_type].add(instance.pk)

    @property
    def created_objects(self) -> Dict[str, List[Model]]:
        """Return a dictionary of Nautobot objects that were created.

        Returns:
            Dict[str, List[BaseModel]]: A dictionary of created objects. The
            keys of the dictionary are the lower case content type labels
            (such as `dcim.device`) and the values are lists of created objects
            of the corresponding type.
        """
        results = {}
        for model_type, pk_list in self.created.items():
            object_list = []
            for primary_key in pk_list:
                instance = model_type.objects.get(pk=primary_key)
                object_list.append(instance)
            results[model_type._meta.label_lower] = object_list
        return results


def _map_query_values(query: Mapping) -> Mapping:
    retval = {}
    for key, value in query.items():
        if isinstance(value, ModelInstance):
            retval[key] = value.instance
        elif isinstance(value, Mapping):
            retval[key] = _map_query_values(value)
        else:
            retval[key] = value
    return retval


class ModelMetadata:  # pylint: disable=too-many-instance-attributes
    """`ModelMetadata` contains all the information design builder needs to track a `ModelInstance`.

    The model metadata includes the query necessary to find a `ModelInstance` in the database, any
    attributes to be updated in the instance, the action to take (get, create, update, etc) and
    additional metadata about the operation (e.g. whether or not the assignment must be deferred).

    In addition to tracking the metadata of an object being manipulated, `ModelMetadata` also
    encapsulates the signal mechanism used by fields and extensions to perform actions based on
    when an object gets saved.
    """

    # Signal Event types
    PRE_SAVE = "PRE_SAVE"
    POST_INSTANCE_SAVE = "POST_INSTANCE_SAVE"
    POST_SAVE = "POST_SAVE"

    # Object Actions
    GET = "get"
    CREATE = "create"
    UPDATE = "update"
    CREATE_OR_UPDATE = "create_or_update"

    ACTION_CHOICES = [GET, CREATE, UPDATE, CREATE_OR_UPDATE]

    def __init__(self, model_instance: "ModelInstance", **kwargs):
        """Initialize the metadata object for a given model instance.

        By default, the metadata object doesn't really have anything in it. In order
        to set the internal values for things like `action` and `kwargs` then the
        attributes setter must be used.

        Args:
            model_instance (ModelInstance): The model instance to which this metadata refers.
        """
        self.model_instance = model_instance
        self.environment = model_instance.environment

        self.created = False

        self._signals = {
            self.PRE_SAVE: [],
            self.POST_INSTANCE_SAVE: [],
            self.POST_SAVE: [],
        }

        self.save_args = kwargs.get("save_args", {})

        # The following attributes are dunder attributes
        # because they should only be set in the @attributes.setter
        # method
        self._action = None
        self._attributes: Dict[str, Any] = {}
        self._custom_fields = {}
        self._deferred = False
        self._filter = {}
        self._kwargs = {}

    @property
    def action(self) -> str:
        """Determine the action.

        This property will always return a value. If no action has been explicitly
        set in a design object, then the default action is `CREATE`. If an action
        has been determined (based on action tags) then that action is returned.

        Returns:
            str: One of the valid values for action: `GET`, `CREATE`, `UPDATE`, `CREATE_OR_UPDATE`
        """
        if self._action is None:
            return self.CREATE
        return self._action

    @action.setter
    def action(self, action: str):
        """Set the action for a given model instance.

        Args:
            action (str): The indicated action (`GET`, `CREATE`, `UPDATE`, `CREATE_OR_UPDATE`)

        This setter confirms that exactly one action type is specified for a model instance.
        The setter may be called multiple times with the same action type. However, if the
        setter is called more than once with different action types then a `DesignImplementationError`
        is raised.

        Raises:
            errors.DesignImplementationError: If an unknown action has been specified or if the
              specified action is different than what was previously set.
        """
        if action not in self.ACTION_CHOICES:
            raise errors.DesignImplementationError(f"Unknown action {action}", self.model_instance.model_class)

        if self._action is None or self._action == action:
            self._action = action
            return

        raise errors.DesignImplementationError(
            f"Can perform only one action for a model, got both {self._action} and {action}",
            self.model_instance.model_class,
        )

    @property
    def attributes(self):
        """Get any attributes that have been processed."""
        return self._attributes

    @attributes.setter
    def attributes(self, attributes: Dict[str, Any]):
        """Process and assign attributes for this metadata.

        Args:
            attributes (Dict[str, Any]): The input attributes to be processed.
              This should be a dictionary of key/value pairs where the keys
              match the field names and properties of a given model type. The
              attributes are processed sequentially. Any action tags are looked up
              and executed in this step.

        Raises:
            errors.DesignImplementationError: A `DesignImplementationError` can be raised
              for a number of different error conditions if an extension cannot be found
              or returns an unknown type. The error can also be raised if a dictionary
              key cannot be mapped to a model field or property.
        """
        self._attributes = {**attributes}
        self._kwargs = {}
        self._filter = {}
        self._custom_fields = self._attributes.pop("custom_fields", {})

        attribute_names = list(self._attributes.keys())
        while attribute_names:
            key = attribute_names.pop(0)
            self._attributes[key] = self.environment.resolve_values(self._attributes[key])
            if key == "deferred":
                self._deferred = self._attributes.pop(key)
            elif key.startswith("!"):
                value = self._attributes.pop(key)
                args = key.lstrip("!").split(":")

                extn: ext.AttributeExtension = self.environment.get_extension("attribute", args[0])
                if extn:
                    result = extn.attribute(*args[1:], value=value, model_instance=self.model_instance)
                    if isinstance(result, tuple):
                        self._attributes[result[0]] = result[1]
                    elif isinstance(result, dict):
                        self._attributes.update(result)
                        attribute_names.extend(result.keys())
                    elif result is not None:
                        raise errors.DesignImplementationError(f"Cannot handle extension return type {type(result)}")
                else:
                    self.action = args[0]
                    self._filter[args[1]] = value
            elif "__" in key:
                fieldname, search = key.split("__", 1)
                if not hasattr(self.model_instance.model_class, fieldname):
                    raise errors.DesignImplementationError(
                        f"{fieldname} is not a property", self.model_instance.model_class
                    )
                self._attributes[fieldname] = {f"!get:{search}": self._attributes.pop(key)}
            elif not hasattr(self.model_instance, key):
                value = self._attributes.pop(key)
                if isinstance(value, ModelInstance):
                    value = value.instance
                self._kwargs[key] = value

    def connect(self, signal: str, handler: FunctionType):
        """Connect a handler between this model instance (as sender) and signal.

        Args:
            signal (str): Signal to listen for.
            handler (FunctionType): Callback function
        """
        self._signals[signal].append(handler)

    def send(self, signal: str):
        """Send a signal to all associated listeners.

        Args:
            signal (str): The signal to send
        """
        for handler in self._signals[signal]:
            handler()
            self.model_instance.instance.refresh_from_db()

    @property
    def custom_fields(self) -> Dict[str, Any]:
        """`custom_fields` property.

        When attributes are processed, the `custom_fields` key is removed and assigned
        to the `custom_fields` property.

        Returns:
            Dict[str, Any]: A dictionary of custom fields/values.
        """
        return self._custom_fields

    @property
    def deferred(self) -> bool:
        """Whether or not this model object's save should be deferred.

        Sometimes a model, specified as a child within a design, must be
        saved after the parent. One good example of this is (in Nautobot 1.x)
        a `Device.primary_ip4`. If the IP address itself is created within
        the device's interface block, and that interface block is defined in the
        same block as the `primary_ip4`, then the `primary_ip4` field cannot be
        set until after the interface's IP has been created. Since the interface
        cannot be created until after the device has been saved (since the interface
        has a required foreign-key field to device) then the sequence must go like this:

        1) Save the new device.
        2) Save the IP address that will be assigned to the interface
        3) Save the interface with foreign keys for device and IP address
        4) Set device's `primary_ip4` and re-save the device.

        The only way to tell design builder to do step 4 last is to set the value on
        the field to `deferred`. This deferral can be specified as in the following example:

        ```yaml
        # Note: the following example is for Nautobot 1.x
        devices:
        - name: "device_1"
            site__name: "site_1"
            status__name: "Active"
            device_type__model: "model name"
            device_role__name: "device role"
            interfaces:
            - name: "Ethernet1/1"
                type: "virtual"
                status__name: "Active"
                description: "description for Ethernet1/1"
                ip_addresses:
                - address: "192.168.56.1/24"
                    status__name: "Active"
            primary_ip4: {"!get:address": "192.168.56.1/24", "deferred": true}
        ```

        Returns:
            bool: Whether or not the object's assignment should be deferred.
        """
        return self._deferred

    @property
    def filter(self):
        """The processed query filter to find the object."""
        return self._filter

    @property
    def kwargs(self):
        """Any keyword arguments needed for the creation of the model object."""
        return self._kwargs

    @property
    def query_filter_values(self):
        """Returns a copy of the query-filter field/values."""
        return {**self._filter}

    @property
    def query_filter(self) -> Dict[str, Any]:
        """Calculate the query filter for the object.

        The `query_filter` property collects all of the lookups for an object
        (set by `!create_or_update` and `!get` tags) and computes a dictionary
        that can be used as keyword arguments to a model manager `.get` method.

        Returns:
            Dict[str, Any]: The computed query filter.
        """
        return _map_query_values(self._filter)


class ModelInstance:
    """An individual object to be created or updated as Design Builder iterates through a rendered design YAML file.

    `ModelInstance` objects are essentially proxy objects between the design builder implementation process
    and normal Django models. The `ModelInstance` intercepts value assignments to fields and properly
    defers database saves so that `ForeignKey` and `ManyToMany` fields are set and saved in the correct order.

    This field proxying also provides a system to model relationships that are more complex than simple
    database fields and relationships (such as Nautobot custom relationships).
    """

    name: str
    model_class: Type[Model]

    @classmethod
    def factory(cls, django_class: Type[Model]) -> "ModelInstance":
        """`factory` takes a normal Django model class and creates a dynamic ModelInstance proxy class.

        Args:
            django_class (Type[Model]): The Django model class to wrap in a proxy class.

        Returns:
            type[ModelInstance]: The newly created proxy class.
        """
        cls_attributes = {
            "model_class": django_class,
            "name": django_class.__name__,
        }

        field: DjangoField
        for field in django_class._meta.get_fields():
            cls_attributes[field.name] = field_factory(None, field)
        model_class = type(django_class.__name__, (ModelInstance,), cls_attributes)
        return model_class

    def __init__(
        self,
        environment: "Environment",
        attributes: dict,
        relationship_manager=None,
        parent=None,
    ):
        """Create a proxy instance for the model.

        This constructor will create a new `ModelInstance` object that wraps a Django
        model instance. All assignments to this instance will be proxied to the underlying
        object using the descriptors in the `fields` module.

        Args:
            environment (Environment): The build environment for the current design.
            attributes (dict): The attributes dictionary for the current object.
            relationship_manager (_type_, optional): The relationship manager to use for lookups. Defaults to None.
            parent (_type_, optional): The parent this object belongs to in the design tree. Defaults to None.

        Raises:
            errors.DoesNotExistError: If the object is being retrieved or updated (not created) and can't be found.
            errors.MultipleObjectsReturnedError: If the object is being retrieved or updated (not created)
                and more than one object matches the lookup criteria.
        """
        self.environment = environment
        self.instance: Model = None
        self.metadata = ModelMetadata(self, **attributes.pop("model_metadata", {}))

        self._parent = parent
        self.refresh_custom_relationships()
        self.relationship_manager = relationship_manager
        if self.relationship_manager is None:
            self.relationship_manager = self.model_class.objects

        self.metadata.attributes = attributes

        try:
            self._load_instance()
        except ObjectDoesNotExist as ex:
            raise errors.DoesNotExistError(self) from ex
        except MultipleObjectsReturned as ex:
            raise errors.MultipleObjectsReturnedError(self) from ex
        self._update_fields()

    def refresh_custom_relationships(self):
        """Look for any custom relationships for this model class and add any new fields."""
        for direction in Relationship.objects.get_for_model(self.model_class):
            for relationship in direction:
                field = field_factory(self, relationship)

                # make sure not to mask non-custom relationship fields that
                # may have the same key name or field name
                for attr_name in [field.key_name, field.field_name]:
                    if hasattr(self.__class__, attr_name):
                        # if there is already an attribute with the same name,
                        # delete it if it is a custom relationship, that way
                        # we reload the config from the database.
                        if isinstance(getattr(self.__class__, attr_name), CustomRelationshipField):
                            delattr(self.__class__, attr_name)
                    if not hasattr(self.__class__, attr_name):
                        setattr(self.__class__, attr_name, field)

    def __str__(self):
        """Get the model class name."""
        return str(self.model_class)

    def create_child(
        self,
        model_class: "ModelInstance",
        attributes: Dict,
        relationship_manager: Manager = None,
    ) -> "ModelInstance":
        """Create a new ModelInstance that is linked to the current instance.

        Args:
            model_class (Type[Model]): Class of the child model.
            attributes (Dict): Design attributes for the child.
            relationship_manager (Manager): Database relationship manager to use for the new instance.

        Returns:
            ModelInstance: Model instance that has its parent correctly set.
        """
        if not issubclass(model_class, ModelInstance):
            model_class = self.environment.model_class_index[model_class]
        try:
            return model_class(
                self.environment,
                attributes,
                relationship_manager,
                parent=self,
            )
        except MultipleObjectsReturned:
            # pylint: disable=raise-missing-from
            raise errors.DesignImplementationError(
                f"Expected exactly 1 object for {model_class.__name__}({attributes}) but got more than one"
            )
        except ObjectDoesNotExist:
            query = ",".join([f'{k}="{v}"' for k, v in attributes.items()])
            # pylint: disable=raise-missing-from
            raise errors.DesignImplementationError(f"Could not find {model_class.__name__}: {query}")

    def connect(self, signal: str, handler: FunctionType):
        """Connect a handler between this model instance (as sender) and signal.

        Args:
            signal (Signal): Signal to listen for.
            handler (FunctionType): Callback function
        """
        self.metadata.connect(signal, handler)

    def _send(self, signal: str):
        self.metadata.send(signal)

    def _load_instance(self):
        query_filter = self.metadata.query_filter
        field_values = self.metadata.query_filter_values
        if self.metadata.action == ModelMetadata.GET:
            self.instance = self.model_class.objects.get(**query_filter)
            return

        if self.metadata.action in [ModelMetadata.UPDATE, ModelMetadata.CREATE_OR_UPDATE]:
            # perform nested lookups. First collect all the
            # query params for top-level relationships, then
            # perform the actual lookup
            for query_param in list(query_filter.keys()):
                if "__" in query_param:
                    value = query_filter.pop(query_param)
                    attribute, filter_param = query_param.split("__", 1)
                    query_filter.setdefault(attribute, {})
                    query_filter[attribute][f"!get:{filter_param}"] = value

            for query_param, value in query_filter.items():
                if isinstance(value, Mapping):
                    rel: Manager = getattr(self.model_class, query_param)
                    queryset: QuerySet = rel.get_queryset()

                    model = self.create_child(
                        self.environment.model_class_index[queryset.model],
                        value,
                        relationship_manager=queryset,
                    )
                    if model.metadata.action != ModelMetadata.GET:
                        model.save()
                    query_filter[query_param] = model.instance
                    field_values[query_param] = model
            try:
                self.instance = self.relationship_manager.get(**query_filter)
                return
            except ObjectDoesNotExist:
                if self.metadata.action == ModelMetadata.UPDATE:
                    # pylint: disable=raise-missing-from
                    raise errors.DesignImplementationError(f"No match with {query_filter}", self.model_class)
        elif self.metadata.action != ModelMetadata.CREATE:
            raise errors.DesignImplementationError(f"Unknown database action {self.metadata.action}", self.model_class)
        # since the object was not found, we need to
        # put the search criteria back into the attributes
        # so that they will be set when the object is created
        self.metadata.attributes.update(field_values)
        self.metadata.created = True
        try:
            self.instance = self.model_class(**self.metadata.kwargs)
        except TypeError as ex:
            raise errors.DesignImplementationError(str(ex), self.model_class)

    def _update_fields(self):
        if self.metadata.action == ModelMetadata.GET:
            if self.metadata.attributes:
                # TODO: Raise a DesignModelError from here. Currently the DesignModelError doesn't
                # include a message.
                raise errors.DesignImplementationError(
                    "Cannot update fields when using the GET action", self.model_class
                )

        for field_name, value in self.metadata.attributes.items():
            if hasattr(self.__class__, field_name):
                setattr(self, field_name, value)
            elif hasattr(self.instance, field_name):
                setattr(self.instance, field_name, value)

            for key, value in self.metadata.custom_fields.items():
                self.set_custom_field(key, value)

    def save(self):
        """Save the model instance to the database.

        This method will save the underlying model object to the database and
        will send signals (`PRE_SAVE`, `POST_INSTANCE_SAVE` and `POST_SAVE`). The
        design journal is updated in this step.
        """
        if self.metadata.action == ModelMetadata.GET:
            return

        self._send(ModelMetadata.PRE_SAVE)

        msg = "Created" if self.metadata.created else "Updated"
        try:
            self.instance.full_clean()
            self.instance.save(**self.metadata.save_args)
            self.environment.journal.log(self)
            self.metadata.created = False
            if self._parent is None:
                self.environment.log_success(
                    message=f"{msg} {self.model_class.__name__} {self.instance}", obj=self.instance
                )
            # Refresh from DB so that we update based on any
            # post save signals that may have fired.
            self.instance.refresh_from_db()
        except ValidationError as validation_error:
            raise errors.DesignValidationError(self) from validation_error

        self._send(ModelMetadata.POST_INSTANCE_SAVE)
        self._send(ModelMetadata.POST_SAVE)

    def set_custom_field(self, field, value):
        """Sets a value for a custom field."""
        self.instance.cf[field] = value


# Don't add models from these app_labels to the
# object creator's list of top level models
_OBJECT_TYPES_APP_FILTER = set(
    [
        "django_celery_beat",
        "admin",
        "users",
        "django_rq",
        "auth",
        "taggit",
        "database",
        "sessions",
        "social_django",
    ]
)


class Environment(LoggingMixin):
    """The design builder build environment.

    The build `Environment` contains all of the components needed to implement a design.
    This includes custom action tag extensions and an optional `JobResult` for logging. The
    build environment also is used by some extensions (such as the `ref` action tag) to store
    information about the designs being implemented.
    """

    model_map: Dict[str, Type[Model]]
    model_class_index: Dict[Type, "ModelInstance"]

    def __new__(cls, *args, **kwargs):
        """Sets the model_map class attribute when the first Builder is initialized."""
        # only populate the model_map once
        if not hasattr(cls, "model_map"):
            cls.model_map = {}
            cls.model_class_index = {}
            for model_class in apps.get_models():
                if model_class._meta.app_label in _OBJECT_TYPES_APP_FILTER:
                    continue
                plural_name = str_to_var_name(model_class._meta.verbose_name_plural)
                cls.model_map[plural_name] = ModelInstance.factory(model_class)
                cls.model_class_index[model_class] = cls.model_map[plural_name]
        return object.__new__(cls)

    def __init__(self, job_result: JobResult = None, extensions: List[ext.Extension] = None):
        """Create a new build environment for implementing designs.

        Args:
            job_result (JobResult, optional): If this environment is being used by
                a `DesignJob` then it can log to the `JobResult` for the job.
                Defaults to None.
            extensions (List[ext.Extension], optional): Any custom extensions to use
                when implementing designs. Defaults to None.

        Raises:
            errors.DesignImplementationError: If a provided extension is not a subclass
                of `ext.Extension`.
        """
        self.job_result = job_result

        self.extensions = {
            "extensions": [],
            "attribute": {},
            "value": {},
        }
        if extensions is None:
            extensions = []

        for extn_cls in [*extensions, *ext.extensions()]:
            if not issubclass(extn_cls, ext.Extension):
                raise errors.DesignImplementationError("{extn_cls} is not an action tag extension.")

            extn = {
                "class": extn_cls,
                "object": None,
            }
            if issubclass(extn_cls, ext.AttributeExtension):
                self.extensions["attribute"][extn_cls.tag] = extn
            if issubclass(extn_cls, ext.ValueExtension):
                self.extensions["value"][extn_cls.tag] = extn

            self.extensions["extensions"].append(extn)

        self.journal = Journal()

    def get_extension(self, ext_type: str, tag: str) -> ext.Extension:
        """Look up an extension based on its tag name and return an instance of that Extension type.

        Args:
            ext_type (str): the type of the extension, i.e. 'attribute' or 'value'
            tag (str): the tag used for the extension, i.e. 'ref' or 'git_context'

        Returns:
            Extension: An instance of the Extension class
        """
        extn = self.extensions[ext_type].get(tag)
        if extn is None:
            return None

        if extn["object"] is None:
            extn["object"] = extn["class"](self)
        return extn["object"]

    def implement_design(self, design: Dict, commit: bool = False):
        """Iterates through items in the design and create them.

        If either commit=False (default) or an exception is raised, then any extensions
        with rollback functionality are called to revert their state. If commit=True
        and no exceptions are raised then the extensions with commit functionality are
        called to finalize changes.

        Args:
            design (Dict): An iterable mapping of design changes.
            commit (bool): Whether or not to commit the transaction. Defaults to False.

        Raises:
            DesignImplementationError: if the model is not in the model map
        """
        if not design:
            raise errors.DesignImplementationError("Empty design")

        try:
            for key, value in design.items():
                if key in self.model_map and value:
                    self._create_objects(self.model_map[key], value)
                else:
                    raise errors.DesignImplementationError(f"Unknown model key {key} in design")
            # TODO: The way this works now the commit happens on a per-design file
            #       basis. If a design job has multiple design files and the first
            #       one completes, but the second one fails, the first will still
            #       have had commit() called. I think this behavior would be considered
            #       unexpected. We need to consider removing the commit/rollback functionality
            #       from `implement_design` and move it to a higher layer, perhaps the `DesignJob`
            if commit:
                self.commit()
            else:
                self.roll_back()
        except Exception as ex:
            self.roll_back()
            raise ex

    def resolve_value(self, value):
        """Resolve a single value using extensions, if needed.

        This method will examine a value to determine if it is an action
        tag. If the value is an action tag, then the corresponding extension
        is called and the result of the extension execution is returned.

        If the value is not an action tag then the original value is returned.
        """
        if isinstance(value, str) and value.startswith("!"):
            (action, arg) = value.lstrip("!").split(":", 1)
            extn = self.get_extension("value", action)
            if extn:
                value = extn.value(arg)
            else:
                raise errors.DesignImplementationError(f"Unknown attribute extension {value}")
        return value

    def resolve_values(self, value: Union[list, dict, str]) -> Any:
        """Resolve a value, or values, using extensions.

        This method is used to evaluate action tags and call their associated
        extensions for a given value tree. The method will iterate the values
        of a list or dictionary and determine if each value represents an
        action tag. If so, the extension for that tag is called and the original
        value is replaced with the result of the extension's execution.

        Lists and dictionaries are copied so that the original values remain un-altered.

        If the value is string and the string is an action tag, that tag is evaluated
        and the result is returned.

        Args:
            value (Union[list,dict,str]): The value to attempt to resolve.

        Returns:
            Any: The resolved value.
        """
        if isinstance(value, str):
            value = self.resolve_value(value)
        elif isinstance(value, list):
            # copy the list so we don't change the input
            value = list(value)
            for i, item in enumerate(value):
                value[i] = self.resolve_value(item)
        elif isinstance(value, dict):
            # copy the dict so we don't change the input
            value = dict(value)
            for k, item in value.items():
                value[k] = self.resolve_value(item)
        return value

    def _create_objects(self, model_class: Type[ModelInstance], objects: Union[List[Any], Dict[str, Any]]):
        if isinstance(objects, dict):
            model = model_class(self, objects)
            model.save()
        elif isinstance(objects, list):
            for model_attributes in objects:
                model = model_class(self, model_attributes)
                model.save()

    def commit(self):
        """The `commit` method iterates all extensions and calls their `commit` methods.

        Some extensions need to perform an action after a design has been successfully
        implemented. For instance, the config context extension waits until after the
        design has been implemented before committing changes to a config context
        repository. The `commit` method will find all extensions that include a `commit`
        method and will call each of them in order.
        """
        for extn in self.extensions["extensions"]:
            if hasattr(extn["object"], "commit"):
                extn["object"].commit()

    def roll_back(self):
        """Looks for any extensions with a roll back method and executes it.

        Used for for rolling back changes that can't be undone with a database rollback, for example config context files.

        """
        for extn in self.extensions["extensions"]:
            if hasattr(extn["object"], "roll_back"):
                extn["object"].roll_back()


def Builder(*args, **kwargs):  # pylint:disable=invalid-name
    """`Builder` is an alias to the `Environment` class.

    This function is used to provide backwards compatible access to the `Builder` class,
    which was renamed to `Environment`. This function will be removed in the future.
    """
    from warnings import warn  # pylint:disable=import-outside-toplevel

    warn("Builder is now named Environment. Please update your code.")
    return Environment(*args, **kwargs)
