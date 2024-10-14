# Design LifeCycle

<!-- TODO: Add the screenshoots -->

According to a design-oriented approach, the Design Builder App provides not only the capacity to create and update data in Nautobot but also a complete lifecycle management of each deployment: update, versioning (in the future), and decommissioning.

<!-- TODO: without an identifier: IDENTIFIER_KEYS = ["!create_or_update", "!create", "!update", "!get"],
the update features are not working as expected.
I would propose to use explicit action tags even for create: "!create:name"
 -->

All the Design Builder UI navigation menus are under the Design Builder tab.

## `Design`

A `Design` is a one to one mapping with a Nautobot `Job`, enriched with some data from the Design Builder `DesignJob` definition. In concrete, it stores:

- A `Job` reference.
- A `version` string from the `DesignJob`.
- A `description` string from the `DesignJob`.
- A `docs` string from the `DesignJob`.

<!-- TODO: Add the screenshoot of the table of Design -->

From the `Design`, the user can manage the associated `Job`, and trigger its execution, which creates a `DesignInstance` or Design Deployment

## Design Deployment or `DesignInstance`

Once a design is "deployed" in Nautobot, a Design Deployment (or `DesignInstance`) is created with the report of the changes implemented (i.e. `Journals`), and with actions to update or decommission it (see next subsections).

The `DesignInstance` stores:

- The `name` of the deployment, within the context of the `Design`.
- The `Design` reference.
- The `version` from the `Design` when it was deployed or updated.
- When it was initially deployed or last updated.
- The `status` of the design, and the `live_state` or operational status to signal its state in the actual network.

<!-- TODO: Add the screenshoot of the table of DesignInstance -->

### Design Deployment Update

This feature provides a means to re-run a design instance with different input data. Re-running the job will update the implemented design with the new changes: additions and removals.

It leverages a complete tracking of previous design implementations and a function to combine the new design and previous design, to understand the changes to be implemented and the objects to be decommissioned (leveraging the previous decommissioning feature for only a specific object).

The update feature comes with a few assumptions:

- All the design objects that have an identifier have to use identifier keys to identify the object to make them comparable across designs.
- Object identifiers should keep consistent in multiple design runs. For example, you can't target a device with the device name and update the name on the same design.
- When design provides a list of objects, the objects are assumed to be in the same order. For example, if the first design creates `[deviceA1, deviceB1]`, if expanded, it should be `[deviceA1, deviceB1, deviceA2, deviceB2]`, not `[deviceA1, deviceA2, deviceB1, deviceB2]`.

<!--
TODO:
- We could check design for update capabilities? to disable when not possible
-->

### Design Deployment Decommission

This feature allows to rollback all the changes implemented by a design instance to the previous state. This rollback depends on the scope of the change:

- If the object was created by the design implementation, this object will be removed.
- If only some attributes were changes, the affected attributes will be rolled back to the previous state.

The decommissioning feature takes into account potential dependencies between design implementations. For example, if a new l3vpn design depends on devices that were created by another design, this previous design won't be decommissioned until the l3vpn dependencies are also decommissioned to warrant consistency.

Once a design instance is decommissioned, it's still visible in the API/UI to check the history of changes but without any active relationship with Nautobot objects. After decommissioning, the design instance can be deleted completely from Nautobot.

There is a decommissioning mode to only remove the link between the design objects and the design deployment without actually reverting the state of the objects. Decommissioning, with the `delete` checkbox _not_ set, is only removing the references but keeping the data.

<!-- TODO: Add the screenshoot of the decommissioning job -->

### Design Deployment Import

Design Builder addresses

- greenfield use cases by creating new data from a design
- brownfield use cases by importing existing data related to a new design deployment

In the "deployment" mode, a design deployment tracks all the objects and attributes that are "owned" by it. With the import functionality, orphan objects and attributes will be incorporated into a new design deployment as if they have been set by it.

The import logic works like this:

1. If the object that we reference doesn't exist, normal design creation logic applies
2. If an object that we want to "create" already exists, normal design creation logic _also_ applies
3. If an object that we want to "create_or_update" already exists
   - If it's not owned by another design deployment, we get "full_control" of it and of all the attributes that we define (including the identifiers)
   - If it already has an owner, we don't claim ownership of the object, but we still may claim the attributes, except the identifiers
4. If an object that we want to "update" already exists
   - There is no claim for "full_control" ownership
   - There is a claim for the attributes, except the identifiers
5. In all cases, the attributes that a design is trying to update are claimed. These attributes can't be claimed by any other design. If so, the import fails pointing to the conflict dependency.
6. The imported changes (attributes) show the same old and new value because we can't infer which was the previous value (in most cases, it would be `null` but we can't be sure)
