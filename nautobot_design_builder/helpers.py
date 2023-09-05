"""This module provides some common provisioning helpers that many designs use."""
from typing import List

from nautobot.dcim.models import Device
from netutils.interface import interface_range_expansion

from nautobot_design_builder.errors import DesignValidationError


class ProvisionerError(DesignValidationError):
    """ProvisionerErrors are raised when some provisioning request cannot be fulfilled."""


class ProvisionerMixin:
    """Provisioner provides helpful methods for provisioning different device components."""

    def __init__(self):
        """Initializes the Provisioner."""
        self._provisioned_interfaces = {}

    def provision_common_interface(
        self, devices: List[Device], interface_range: str = None, search_criteria=None
    ) -> str:
        """Provision the same interface (by name) across a list of devices.

        This method will search for the first matching interface (using provision_device_interface)
        of each device. If the set of interfaces all share the same name, then that name is returned.
        If any of the names differ, then a ProvisionerError is raised.

        Args:
            devices (List[Device]): List of devices to provision from
            interface_range (str, optional): The interface range to look in. This is a string expanded by interface_range_expansion
            search_criteria (dict, optional): Additional search criteria for the Interface lookup. Defaults to None.

        Raises:
            ProvisionerError: raised if no matching interface is found, or if not all interface have the same name.

        Returns:
            str: Interface name that was provisioned in each of the devices.
        """
        interfaces = [
            self.provision_device_interface(
                device,
                interface_range,
                search_criteria,
            )
            for device in devices
        ]

        if not all((interface == interfaces[0] for interface in interfaces)):
            raise ProvisionerError("Failed to find spine ports of the same name")

        return interfaces[0]

    def provision_device_interface(self, device: Device, interface_range: str = None, search_criteria=None) -> str:
        """Return an interface where the name is within the range.

        If no interface is found between the range (and matching the optional
        search criteria) then a ProvisionerError is raised. Subsequent calls
        of this method should return a new interface until there are no
        longer any available interfaces. Note: the database is not change,
        the memory of what interfaces have been provisioned is local to the
        current instance of Provisioner. It is assumed that once a design
        is ready to be implemented all provisioned interfaces will be updated
        in the design.

        Args:
            device: The device to look for a free interface
            interface_range: The interface range to look in. This is a string expanded by interface_range_expansion
            search_criteria: dictionary that is passed to the ORM filter. Logic
                for determining free interfaces should be in this filter

        Returns:
            interface name that has been set aside

        Raises:
            ProvisionerError: No available interfaces
        """
        if search_criteria is None:
            search_criteria = {}

        if interface_range:
            search_criteria["name__in"] = interface_range_expansion(interface_range)

        interfaces: List[Device] = device.interfaces.filter(**search_criteria)
        for interface in interfaces:
            if interface.name not in self._provisioned_interfaces.get(device.id, set()):
                self._provisioned_interfaces.setdefault(device.id, set())
                self._provisioned_interfaces[device.id].add(interface.name)
                return interface.name
        raise ProvisionerError(f"No available interfaces for {device} in {interface_range}")
