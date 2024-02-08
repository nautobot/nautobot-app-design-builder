"""Temporal file that includes the recursive functions used to manipulate designs."""

import itertools
from nautobot_design_builder.errors import DesignImplementationError
from nautobot_design_builder.constants import NAUTOBOT_ID, IDENTIFIER_KEYS


def get_object_identifier(obj):
    """Returns de object identifier value, if it exists."""
    # TODO: add a note in the docs about design best practices
    # The object identifier should be consistent in all the design implementations, not updating it
    for key in obj:
        if any(identifier_key in key for identifier_key in IDENTIFIER_KEYS):
            return obj[key]
    return None


def inject_nautobot_uuids(initial_data, final_data):
    """This recursive function update the output design adding the Nautobot identifier."""
    if isinstance(initial_data, list):
        for item1 in initial_data:
            item1_identifier = get_object_identifier(item1)
            if item1_identifier:
                for item2 in final_data:
                    item2_identifier = get_object_identifier(item2)
                    if item2_identifier == item1_identifier:
                        inject_nautobot_uuids(item1, item2)
                        break
    elif isinstance(initial_data, dict):
        new_data_identifier = get_object_identifier(final_data)
        data_identifier = get_object_identifier(initial_data)

        for key in initial_data:
            # TODO: We only recurse it for lists, not found a use case for dicts
            if isinstance(initial_data[key], list):
                inject_nautobot_uuids(initial_data[key], final_data[key])

            # Other special keys (extensions), not identifiers
            elif "!" in key and not any(identifier_key in key for identifier_key in IDENTIFIER_KEYS):
                inject_nautobot_uuids(initial_data[key], final_data[key])

        # TODO: for ext:connect_cable how do I know is the same object? both identifiers are None
        if data_identifier == new_data_identifier:
            final_data[NAUTOBOT_ID] = initial_data[NAUTOBOT_ID]


# TODO: could we make it simpler?
def reduce_design(
    new_value, old_value, future_value, decommissioned_objects, type_key
):  # pylint: disable=too-many-locals,too-many-return-statements,too-many-branches,too-many-statements
    """Recursive function to simplify the new design by comparing with a previous design.

    Args:
        new_value: New design element.
        old_value: Previous design element.
        future_value: Final design element to be persisted for future reference.
        decommissioned_objects: Elements that are no longer relevant and will be decommissioned.
        type_key: Reference key in the design element.

    """
    if isinstance(new_value, list):
        objects_to_decommission = []

        for new_element, old_element, future_element in itertools.zip_longest(
            new_value.copy(), old_value, future_value
        ):
            # TODO: add a note in the docs about design best practices
            # It's assumed that the design will generated lists where the objects are on the same place

            if new_element is None:
                # This means that this is one element that was existing before, but it's no longer in the design
                # Therefore, it must be decommissioned if it's a dictionary, that's a potential design object
                if isinstance(old_element, dict):
                    objects_to_decommission.append((old_element.get(NAUTOBOT_ID), get_object_identifier(old_element)))

            elif old_element is None:
                # If it is a new element in the design, we keep it as it is.
                pass

            elif isinstance(new_element, dict) and isinstance(old_element, dict):
                old_nautobot_identifier = old_element.get(NAUTOBOT_ID)
                new_elem_identifier = get_object_identifier(new_element)
                old_elem_identifier = get_object_identifier(old_element)
                if new_elem_identifier != old_elem_identifier:
                    # If the objects in the same list position are not the same (based on the design identifier),
                    # the old element is added to the decommissioning list, and a recursive process to decommission
                    # all the related children objects is initiated
                    # TODO: One possible situation is that a cable of a nested interface in the same object
                    # is added into the nested reduce design, but the nautobot identifier is lost to
                    # be taken into account to be decommissioned before. Maybe we could move the nautobot identifiers to the new object?

                    objects_to_decommission.append((old_nautobot_identifier, old_elem_identifier))

                    reduce_design({}, old_element, {}, decommissioned_objects, type_key)

                # When the elements have the same identifier, we progress on the recursive reduction analysis
                elif reduce_design(new_element, old_element, future_element, decommissioned_objects, type_key):
                    # As we are iterating over the new_value list, we keep the elements that the `reduce_design`
                    # concludes that must be deleted as not longer relevant for the new design.
                    new_value.remove(new_element)

            else:
                raise DesignImplementationError("Unexpected type of object.")

        if objects_to_decommission:
            # All the elements marked for decommissioning are added to the mutable `decommissioned_objects` dictionary
            # that will later revert the object changes done by this design.
            if type_key not in decommissioned_objects:
                decommissioned_objects[type_key] = []
            decommissioned_objects[type_key].extend(objects_to_decommission)

        # If the final result of the new_value list is empty (i.e., all the elements are no relevant),
        # The function returns True to signal that the calling entity can be also reduced.
        if new_value == []:
            return True

        return False

    if isinstance(new_value, dict):
        # Removing the old Nautobot identifier to simplify comparison
        old_nautobot_identifier = old_value.pop(NAUTOBOT_ID, None)

        # When the objects are exactly the same (i.e., same values and no identifiers, including nested objects)
        # The nautobot identifier must be persisted in the new design values, but the object may be reduced
        # from the new design to implement (i.e., returning True)
        if new_value == old_value:
            if old_nautobot_identifier:
                future_value[NAUTOBOT_ID] = old_nautobot_identifier
                new_value[NAUTOBOT_ID] = old_nautobot_identifier

            # If the design object contains any reference to a another design object, it can't be
            # reduced because maybe the referenced object is changing
            for inner_key in new_value:
                if isinstance(new_value[inner_key], str) and "!ref:" in new_value[inner_key]:
                    return False

            # If the design object is a reference for other design objects, it can't be reduced.
            if "!ref" in new_value:
                return False

            return True

        identifier_old_value = get_object_identifier(old_value)

        for inner_old_key in old_value:
            if inner_old_key == NAUTOBOT_ID and "!" in inner_old_key:
                continue

            # Reseting desired values for attributes not included in the new design implementation
            # TODO: not sure why do we need this
            if inner_old_key not in new_value:
                new_value[inner_old_key] = None

        identifier_new_value = get_object_identifier(new_value)

        for inner_key, inner_value in new_value.copy().items():
            if any(identifier_key in inner_key for identifier_key in IDENTIFIER_KEYS + ["!ref"]):
                continue

            if (
                identifier_new_value
                and identifier_new_value == identifier_old_value
                and "!" not in inner_key
                and inner_key in old_value
                and new_value[inner_key] == old_value[inner_key]
            ):
                # If the values of the attribute in the design are the same, remove it for simplification
                del new_value[inner_key]

            elif not inner_value and isinstance(old_value[inner_key], list):
                # If the old value was a list, and it doesn't exist in the new design object
                # we append to the objects to decommission all the list objects, calling the recursive reduction
                for obj in old_value[inner_key]:
                    if inner_key not in decommissioned_objects:
                        decommissioned_objects[inner_key] = []

                    decommissioned_objects[inner_key].append((obj[NAUTOBOT_ID], get_object_identifier(obj)))
                    reduce_design({}, obj, {}, decommissioned_objects, inner_key)

            elif isinstance(inner_value, (dict, list)) and inner_key in old_value:
                # If an attribute is a dict or list, explore it recursively to reduce it
                if reduce_design(
                    inner_value,
                    old_value[inner_key],
                    future_value[inner_key],
                    decommissioned_objects,
                    inner_key,
                ):
                    del new_value[inner_key]

        # Reuse the Nautobot identifier for the future design in all cases
        if old_nautobot_identifier and identifier_new_value == identifier_old_value:
            future_value[NAUTOBOT_ID] = old_nautobot_identifier

        # If at this point we only have an identifier, remove the object, no need to mess it up
        if len(new_value) <= 1:
            return True

        # Reuse the Nautobot identifier for the current design only when there is need to keep it in the design
        if old_nautobot_identifier and identifier_new_value == identifier_old_value:
            new_value[NAUTOBOT_ID] = old_nautobot_identifier

        return False

    raise DesignImplementationError("The design reduction only works for dict or list objects.")
