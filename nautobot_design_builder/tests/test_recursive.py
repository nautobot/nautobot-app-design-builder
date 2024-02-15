"""Unit tests related to the recursive functions for reducing and updating designs."""

import copy
import unittest


from nautobot_design_builder.recursive import reduce_design, inject_nautobot_uuids


# pylint: disable=missing-class-docstring


# TODO: Refactor this tests to use a parametrized approach
class TestRecursive(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None  # pylint: disable=invalid-name

    def test_update_output_design_1(self):
        deferred_data = {
            "interfaces": [
                {
                    "!create_or_update:name": "Vlan1",
                    "ip_addresses": [
                        {
                            "!create_or_update:address": "10.250.0.6/30",
                            "status__name": "Reserved",
                            "nautobot_identifier": "0bd5ff9d-1457-4935-8b85-78f2a6defee4",
                        }
                    ],
                    "nautobot_identifier": "dc0cf235-305a-4553-afb9-1f0d0e6eba93",
                }
            ]
        }
        goal_data = {
            "!update:name": "Device 1",
            "site__name": "Site 1",
            "location__name": "Location 1",
            "device_role__slug": "ces",
            "status__name": "Planned",
            "interfaces": [
                {
                    "!update:name": "GigabitEthernet1/0/1",
                    "!connect_cable": {
                        "status__name": "Planned",
                        "to": {"device__name": "Device 2", "name": "GigabitEthernet0/0/0"},
                        "nautobot_identifier": "dab03f25-58be-4185-9daf-0deff326543f",
                    },
                    "nautobot_identifier": "ed0de1c0-2d99-4b83-ac5f-8fe4c03cac14",
                },
                {
                    "!update:name": "GigabitEthernet1/0/14",
                    "!connect_cable": {
                        "status__name": "Planned",
                        "to": {"device__name": "Device 4", "name": "GigabitEthernet0/0/0"},
                        "nautobot_identifier": "44198dd4-5e71-4f75-b4f6-c756b16c30bc",
                    },
                    "nautobot_identifier": "b8321d58-1266-4ed3-a55d-92c25a1adb88",
                },
                {
                    "!create_or_update:name": "Vlan1",
                    "status__name": "Planned",
                    "type": "virtual",
                    "ip_addresses": [
                        {
                            "!create_or_update:address": "10.250.0.6/30",
                            "status__name": "Reserved",
                            "nautobot_identifier": "0bd5ff9d-1457-4935-8b85-78f2a6defee4",
                        }
                    ],
                    "nautobot_identifier": "dc0cf235-305a-4553-afb9-1f0d0e6eba93",
                },
            ],
            "nautobot_identifier": "d93ca54a-6123-4792-b7d9-d730a6fddaa4",
        }
        future_data = {
            "!update:name": "Device 1",
            "site__name": "Site 1",
            "location__name": "Location 1",
            "device_role__slug": "ces",
            "status__name": "Planned",
            "interfaces": [
                {
                    "!update:name": "GigabitEthernet1/0/1",
                    "!connect_cable": {
                        "status__name": "Planned",
                        "to": {"device__name": "Device 2", "name": "GigabitEthernet0/0/0"},
                        "nautobot_identifier": "dab03f25-58be-4185-9daf-0deff326543f",
                    },
                    "nautobot_identifier": "ed0de1c0-2d99-4b83-ac5f-8fe4c03cac14",
                },
                {
                    "!update:name": "GigabitEthernet1/0/14",
                    "!connect_cable": {
                        "status__name": "Planned",
                        "to": {"device__name": "Device 4", "name": "GigabitEthernet0/0/0"},
                        "nautobot_identifier": "44198dd4-5e71-4f75-b4f6-c756b16c30bc",
                    },
                    "nautobot_identifier": "b8321d58-1266-4ed3-a55d-92c25a1adb88",
                },
                {
                    "!create_or_update:name": "Vlan1",
                    "status__name": "Planned",
                    "type": "virtual",
                    "ip_addresses": [{"!create_or_update:address": "10.250.0.6/30", "status__name": "Reserved"}],
                    "nautobot_identifier": "dc0cf235-305a-4553-afb9-1f0d0e6eba93",
                },
            ],
            "nautobot_identifier": "d93ca54a-6123-4792-b7d9-d730a6fddaa4",
        }
        inject_nautobot_uuids(deferred_data, future_data)
        self.assertEqual(future_data, goal_data)

    def test_update_output_design_2(self):
        deferred_data = {
            "interfaces": [
                {
                    "!update:name": "GigabitEthernet1/0/1",
                    "!connect_cable": {
                        "status__name": "Planned",
                        "to": {"device__name": "Device 2", "name": "GigabitEthernet0/0/0"},
                        "nautobot_identifier": "8322e248-a872-4b54-930e-e8fe5a1ad4d0",
                    },
                    "nautobot_identifier": "ed0de1c0-2d99-4b83-ac5f-8fe4c03cac14",
                },
                {
                    "!update:name": "GigabitEthernet1/0/14",
                    "!connect_cable": {
                        "status__name": "Planned",
                        "to": {"device__name": "Device 4", "name": "GigabitEthernet0/0/0"},
                        "nautobot_identifier": "c514cdf9-754e-4c1c-b1ff-eddb17d396d4",
                    },
                    "nautobot_identifier": "b8321d58-1266-4ed3-a55d-92c25a1adb88",
                },
                {
                    "!create_or_update:name": "Vlan1",
                    "status__name": "Planned",
                    "type": "virtual",
                    "ip_addresses": [
                        {
                            "!create_or_update:address": "10.250.0.2/30",
                            "status__name": "Reserved",
                            "nautobot_identifier": "8f910a91-395f-4c00-adfc-303121dc5d69",
                        }
                    ],
                    "nautobot_identifier": "acca93cf-813f-4cd5-a15b-90847d5fe118",
                },
            ]
        }
        goal_data = {
            "!update:name": "Device 1",
            "site__name": "Site 1",
            "location__name": "Location 1",
            "device_role__slug": "ces",
            "status__name": "Planned",
            "interfaces": [
                {
                    "!update:name": "GigabitEthernet1/0/1",
                    "!connect_cable": {
                        "status__name": "Planned",
                        "to": {"device__name": "Device 2", "name": "GigabitEthernet0/0/0"},
                        "nautobot_identifier": "8322e248-a872-4b54-930e-e8fe5a1ad4d0",
                    },
                    "nautobot_identifier": "ed0de1c0-2d99-4b83-ac5f-8fe4c03cac14",
                },
                {
                    "!update:name": "GigabitEthernet1/0/14",
                    "!connect_cable": {
                        "status__name": "Planned",
                        "to": {"device__name": "Device 4", "name": "GigabitEthernet0/0/0"},
                        "nautobot_identifier": "c514cdf9-754e-4c1c-b1ff-eddb17d396d4",
                    },
                    "nautobot_identifier": "b8321d58-1266-4ed3-a55d-92c25a1adb88",
                },
                {
                    "!create_or_update:name": "Vlan1",
                    "status__name": "Planned",
                    "type": "virtual",
                    "ip_addresses": [
                        {
                            "!create_or_update:address": "10.250.0.2/30",
                            "status__name": "Reserved",
                            "nautobot_identifier": "8f910a91-395f-4c00-adfc-303121dc5d69",
                        }
                    ],
                    "nautobot_identifier": "acca93cf-813f-4cd5-a15b-90847d5fe118",
                },
            ],
            "nautobot_identifier": "d93ca54a-6123-4792-b7d9-d730a6fddaa4",
        }
        future_data = {
            "!update:name": "Device 1",
            "site__name": "Site 1",
            "location__name": "Location 1",
            "device_role__slug": "ces",
            "status__name": "Planned",
            "interfaces": [
                {
                    "!update:name": "GigabitEthernet1/0/1",
                    "!connect_cable": {
                        "status__name": "Planned",
                        "to": {"device__name": "Device 2", "name": "GigabitEthernet0/0/0"},
                    },
                },
                {
                    "!update:name": "GigabitEthernet1/0/14",
                    "!connect_cable": {
                        "status__name": "Planned",
                        "to": {"device__name": "Device 4", "name": "GigabitEthernet0/0/0"},
                    },
                },
                {
                    "!create_or_update:name": "Vlan1",
                    "status__name": "Planned",
                    "type": "virtual",
                    "ip_addresses": [{"!create_or_update:address": "10.250.0.2/30", "status__name": "Reserved"}],
                },
            ],
            "nautobot_identifier": "d93ca54a-6123-4792-b7d9-d730a6fddaa4",
        }
        inject_nautobot_uuids(deferred_data, future_data)
        self.assertEqual(future_data, goal_data)

    def test_reduce_design_1(self):
        design = {
            "prefixes": [
                {
                    "!create_or_update:prefix": "10.255.0.0/32",
                    "status__name": "Active",
                    "description": "co-intraprefix-01 Instance:a",
                },
                {
                    "!create_or_update:prefix": "10.255.0.1/32",
                    "status__name": "Active",
                    "description": "ce01-intraprefix Instance:a",
                },
                {
                    "!create_or_update:prefix": "10.250.0.4/30",
                    "status__name": "Active",
                    "description": "ce-ces Mgmt Instance:a",
                },
                {
                    "!create_or_update:prefix": "10.250.100.4/30",
                    "status__name": "Active",
                    "description": "co-cer Mgmt Instance:a",
                },
            ],
            "devices": [
                {
                    "!update:name": "Device 1",
                    "site__name": "Site 1",
                    "location__name": "Location 1",
                    "device_role__slug": "ces",
                    "status__name": "Planned",
                    "interfaces": [
                        {
                            "!update:name": "GigabitEthernet1/0/1",
                            "!connect_cable": {
                                "status__name": "Planned",
                                "to": {"device__name": "Device 2", "name": "GigabitEthernet0/0/0"},
                            },
                        },
                        {
                            "!update:name": "GigabitEthernet1/0/14",
                            "!connect_cable": {
                                "status__name": "Planned",
                                "to": {"device__name": "Device 4", "name": "GigabitEthernet0/0/0"},
                            },
                        },
                        {
                            "!create_or_update:name": "Vlan1",
                            "status__name": "Planned",
                            "type": "virtual",
                            "ip_addresses": [
                                {"!create_or_update:address": "10.250.0.6/30", "status__name": "Reserved"}
                            ],
                        },
                    ],
                },
                {
                    "!update:name": "Device 2",
                    "site__name": "Site 1",
                    "location__name": "Location 1",
                    "device_role__slug": "ce",
                    "status__name": "Planned",
                    "interfaces": [
                        {
                            "!update:name": "Ethernet0/2/0",
                            "!connect_cable": {
                                "status__name": "Planned",
                                "to": {"device__name": "Device 3", "name": "Ethernet0/2/0"},
                            },
                            "ip_addresses": [
                                {"!create_or_update:address": "10.250.100.5/30", "status__name": "Reserved"}
                            ],
                        },
                        {
                            "!create_or_update:name": "lo10",
                            "status__name": "Planned",
                            "type": "virtual",
                            "ip_addresses": [
                                {"!create_or_update:address": "10.255.0.0/32", "status__name": "Reserved"}
                            ],
                        },
                    ],
                },
                {
                    "!update:name": "Device 3",
                    "site__name": "Site 2",
                    "location__name": "Location 2",
                    "device_role__slug": "cer",
                    "status__name": "Planned",
                    "interfaces": [
                        {
                            "!update:name": "Ethernet0/2/0",
                            "ip_addresses": [
                                {"!create_or_update:address": "10.250.100.6/30", "status__name": "Reserved"}
                            ],
                        },
                        {
                            "!create_or_update:name": "lo10",
                            "status__name": "Planned",
                            "type": "virtual",
                            "ip_addresses": [
                                {"!create_or_update:address": "10.255.0.1/32", "status__name": "Reserved"}
                            ],
                        },
                    ],
                },
            ],
        }
        previous_design = {
            "devices": [
                {
                    "interfaces": [
                        {
                            "!update:name": "GigabitEthernet1/0/1",
                            "!connect_cable": {
                                "to": {"name": "GigabitEthernet0/0/0", "device__name": "Device 2"},
                                "status__name": "Planned",
                                "nautobot_identifier": "0fd83863-6bf6-4a32-b056-1c14970307e1",
                            },
                            "nautobot_identifier": "91772985-9564-4176-9232-94b12d30c0c3",
                        },
                        {
                            "!update:name": "GigabitEthernet1/0/14",
                            "!connect_cable": {
                                "to": {"name": "GigabitEthernet0/0/0", "device__name": "Device 4"},
                                "status__name": "Planned",
                                "nautobot_identifier": "5e2cc3a6-b47e-4070-8ca2-5df738e29774",
                            },
                            "nautobot_identifier": "b783c298-c398-4498-9ecc-50ffcb9d0364",
                        },
                        {
                            "type": "virtual",
                            "ip_addresses": [
                                {
                                    "status__name": "Reserved",
                                    "nautobot_identifier": "c844e64d-b8e1-4226-80ef-c938f8177793",
                                    "!create_or_update:address": "10.250.0.2/30",
                                }
                            ],
                            "status__name": "Planned",
                            "nautobot_identifier": "ed91b2fc-cc4a-4726-82fc-07facbb429bb",
                            "!create_or_update:name": "Vlan1",
                        },
                    ],
                    "site__name": "Site 1",
                    "!update:name": "Device 1",
                    "status__name": "Planned",
                    "location__name": "Location 1",
                    "device_role__slug": "ces",
                    "nautobot_identifier": "a6165def-a1a7-4c0d-8f96-aa6f7e3b83d2",
                },
                {
                    "interfaces": [
                        {
                            "!update:name": "Ethernet0/2/0",
                            "ip_addresses": [
                                {
                                    "status__name": "Reserved",
                                    "nautobot_identifier": "33943833-8ab4-473c-a64d-5b45d54d1d46",
                                    "!create_or_update:address": "10.250.100.1/30",
                                }
                            ],
                            "!connect_cable": {
                                "to": {"name": "Ethernet0/2/0", "device__name": "Device 3"},
                                "status__name": "Planned",
                                "nautobot_identifier": "f321b2b4-421f-481a-9955-1f4347e14f6c",
                            },
                            "nautobot_identifier": "259a7a35-5336-4a45-aa74-27be778358a2",
                        },
                        {
                            "type": "virtual",
                            "ip_addresses": [
                                {
                                    "status__name": "Reserved",
                                    "nautobot_identifier": "6a4e36f2-9231-4618-b091-9f5fbebfb387",
                                    "!create_or_update:address": "10.255.0.0/32",
                                }
                            ],
                            "status__name": "Planned",
                            "nautobot_identifier": "65832777-e48e-4d5d-984c-e9fa32e3f7df",
                            "!create_or_update:name": "lo10",
                        },
                    ],
                    "site__name": "Site 1",
                    "!update:name": "Device 2",
                    "status__name": "Planned",
                    "location__name": "Location 1",
                    "device_role__slug": "ce",
                    "nautobot_identifier": "1cc796cd-4c2c-47c4-af60-3c56f69965f8",
                },
                {
                    "interfaces": [
                        {
                            "!update:name": "Ethernet0/2/0",
                            "ip_addresses": [
                                {
                                    "status__name": "Reserved",
                                    "nautobot_identifier": "d50d3b01-e59d-431f-b91d-46c5a933afe8",
                                    "!create_or_update:address": "10.250.100.2/30",
                                }
                            ],
                            "nautobot_identifier": "c9ae176d-ea86-4844-a5e7-cd331b9c9491",
                        },
                        {
                            "type": "virtual",
                            "ip_addresses": [
                                {
                                    "status__name": "Reserved",
                                    "nautobot_identifier": "be9b9a70-78ee-407c-93cf-55231718e5c7",
                                    "!create_or_update:address": "10.255.0.1/32",
                                }
                            ],
                            "status__name": "Planned",
                            "nautobot_identifier": "2e4bc2ec-a837-4fc0-87b7-5fa6b9847532",
                            "!create_or_update:name": "lo10",
                        },
                    ],
                    "site__name": "Site 2",
                    "!update:name": "Device 3",
                    "status__name": "Planned",
                    "location__name": "Location 2",
                    "device_role__slug": "cer",
                    "nautobot_identifier": "2509af45-70e0-4708-87ca-8203b8570819",
                },
            ],
            "prefixes": [
                {
                    "description": "co-intraprefix-01 Instance:a",
                    "status__name": "Active",
                    "nautobot_identifier": "4f2e9d74-3e3b-4231-a8b8-430726db0e1c",
                    "!create_or_update:prefix": "10.255.0.0/32",
                },
                {
                    "description": "ce01-intraprefix Instance:a",
                    "status__name": "Active",
                    "nautobot_identifier": "6a109931-9194-4748-95d8-042156b786d8",
                    "!create_or_update:prefix": "10.255.0.1/32",
                },
                {
                    "description": "ce-ces Mgmt Instance:a",
                    "status__name": "Active",
                    "nautobot_identifier": "0804b67b-ec96-4f79-96c0-e7750fd42b5a",
                    "!create_or_update:prefix": "10.250.0.0/30",
                },
                {
                    "description": "co-cer Mgmt Instance:a",
                    "status__name": "Active",
                    "nautobot_identifier": "9806c31b-a01d-4537-bf08-ba2db697052e",
                    "!create_or_update:prefix": "10.250.100.0/30",
                },
            ],
        }
        goal_design = {
            "prefixes": [
                {
                    "!create_or_update:prefix": "10.250.0.4/30",
                    "description": "ce-ces Mgmt Instance:a",
                    "status__name": "Active",
                },
                {
                    "!create_or_update:prefix": "10.250.100.4/30",
                    "description": "co-cer Mgmt Instance:a",
                    "status__name": "Active",
                },
            ],
            "devices": [
                {
                    "!update:name": "Device 1",
                    "interfaces": [
                        {
                            "!create_or_update:name": "Vlan1",
                            "ip_addresses": [
                                {"!create_or_update:address": "10.250.0.6/30", "status__name": "Reserved"}
                            ],
                            "nautobot_identifier": "ed91b2fc-cc4a-4726-82fc-07facbb429bb",
                        }
                    ],
                    "nautobot_identifier": "a6165def-a1a7-4c0d-8f96-aa6f7e3b83d2",
                },
                {
                    "!update:name": "Device 2",
                    "interfaces": [
                        {
                            "!update:name": "Ethernet0/2/0",
                            "ip_addresses": [
                                {"!create_or_update:address": "10.250.100.5/30", "status__name": "Reserved"}
                            ],
                            "nautobot_identifier": "259a7a35-5336-4a45-aa74-27be778358a2",
                        }
                    ],
                    "nautobot_identifier": "1cc796cd-4c2c-47c4-af60-3c56f69965f8",
                },
                {
                    "!update:name": "Device 3",
                    "interfaces": [
                        {
                            "!update:name": "Ethernet0/2/0",
                            "ip_addresses": [
                                {"!create_or_update:address": "10.250.100.6/30", "status__name": "Reserved"}
                            ],
                            "nautobot_identifier": "c9ae176d-ea86-4844-a5e7-cd331b9c9491",
                        }
                    ],
                    "nautobot_identifier": "2509af45-70e0-4708-87ca-8203b8570819",
                },
            ],
        }
        goal_elements_to_be_decommissioned = {
            "prefixes": [
                ("0804b67b-ec96-4f79-96c0-e7750fd42b5a", "10.250.0.0/30"),
                ("9806c31b-a01d-4537-bf08-ba2db697052e", "10.250.100.0/30"),
            ],
            "ip_addresses": [
                ("c844e64d-b8e1-4226-80ef-c938f8177793", "10.250.0.2/30"),
                ("33943833-8ab4-473c-a64d-5b45d54d1d46", "10.250.100.1/30"),
                ("d50d3b01-e59d-431f-b91d-46c5a933afe8", "10.250.100.2/30"),
            ],
        }
        elements_to_be_decommissioned = {}
        future_design = copy.deepcopy(design)
        ext_keys_to_be_simplified = []
        for key, new_value in design.items():
            old_value = previous_design[key]
            future_value = future_design[key]
            to_delete = reduce_design(new_value, old_value, future_value, elements_to_be_decommissioned, key)
            if to_delete:
                ext_keys_to_be_simplified.append(key)

        for key, value in goal_design.items():
            self.assertEqual(value, design[key])

        for key, value in goal_elements_to_be_decommissioned.items():
            self.assertEqual(value, elements_to_be_decommissioned[key])

    def test_reduce_design_2(self):
        design = {
            "manufacturers": [{"!create_or_update:name": "Juniper", "slug": "juniper"}],
            "device_types": [
                {
                    "!create_or_update:model": "PTX10016",
                    "slug": "ptx10016",
                    "manufacturer__slug": "juniper",
                    "u_height": 21,
                }
            ],
            "device_roles": [{"!create_or_update:name": "Core Router", "slug": "core_router", "color": "3f51b5"}],
            "regions": {
                "!create_or_update:name": "Americas",
                "children": [
                    {
                        "!create_or_update:name": "United States",
                        "children": [
                            {
                                "!create_or_update:name": "US-East-1",
                                "sites": [
                                    {"!create_or_update:name": "IAD5", "status__name": "Active", "!ref": "iad5"},
                                    {"!create_or_update:name": "LGA1", "status__name": "Active", "!ref": "lga1"},
                                ],
                            },
                            {
                                "!create_or_update:name": "US-West-1",
                                "sites": [
                                    {"!create_or_update:name": "LAX11", "status__name": "Active", "!ref": "lax11"},
                                    {"!create_or_update:name": "SEA1", "status__name": "Active", "!ref": "sea1"},
                                ],
                            },
                        ],
                    }
                ],
            },
            "devices": [
                {
                    "!create_or_update:name": "core0.iad5",
                    "site": "!ref:iad5",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
                {
                    "!create_or_update:name": "core0.lga1",
                    "site": "!ref:lga1",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
                {
                    "!create_or_update:name": "core0.lax11",
                    "site": "!ref:lax11",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
                {
                    "!create_or_update:name": "core0.sea1",
                    "site": "!ref:sea1",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
                {
                    "!create_or_update:name": "core1.iad5",
                    "site": "!ref:iad5",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
                {
                    "!create_or_update:name": "core1.lga1",
                    "site": "!ref:lga1",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
                {
                    "!create_or_update:name": "core1.lax11",
                    "site": "!ref:lax11",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
                {
                    "!create_or_update:name": "core1.sea1",
                    "site": "!ref:sea1",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
            ],
        }
        previous_design = {
            "devices": [
                {
                    "site": "!ref:iad5",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "ff4bb89f-972b-4b86-9055-a6a8291703b0",
                    "!create_or_update:name": "core0.iad5",
                },
                {
                    "site": "!ref:lga1",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "d2c289ed-e1c2-4643-a5bc-0768fa037b2d",
                    "!create_or_update:name": "core0.lga1",
                },
                {
                    "site": "!ref:lax11",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "503452bf-54b1-472b-846e-dc0bb5b42f67",
                    "!create_or_update:name": "core0.lax11",
                },
                {
                    "site": "!ref:sea1",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "d5b6ae22-c32c-4722-a350-254ff2caad18",
                    "!create_or_update:name": "core0.sea1",
                },
            ],
            "regions": {
                "children": [
                    {
                        "children": [
                            {
                                "sites": [
                                    {
                                        "!ref": "iad5",
                                        "status__name": "Active",
                                        "nautobot_identifier": "a45b4b25-1e78-4c7b-95ad-b2880143cc19",
                                        "!create_or_update:name": "IAD5",
                                    },
                                    {
                                        "!ref": "lga1",
                                        "status__name": "Active",
                                        "nautobot_identifier": "70232953-55f0-41c9-b5bb-bc23d6d88906",
                                        "!create_or_update:name": "LGA1",
                                    },
                                ],
                                "nautobot_identifier": "76a1c915-7b30-426b-adef-9721fb768fce",
                                "!create_or_update:name": "US-East-1",
                            },
                            {
                                "sites": [
                                    {
                                        "!ref": "lax11",
                                        "status__name": "Active",
                                        "nautobot_identifier": "5482d5c6-e4f7-4577-b3c0-50a396872f14",
                                        "!create_or_update:name": "LAX11",
                                    },
                                    {
                                        "!ref": "sea1",
                                        "status__name": "Active",
                                        "nautobot_identifier": "618d24ac-6ccf-4f86-a0bd-c3e816cc9919",
                                        "!create_or_update:name": "SEA1",
                                    },
                                ],
                                "nautobot_identifier": "28a13a4a-9b08-4407-b407-c094d19eaf68",
                                "!create_or_update:name": "US-West-1",
                            },
                        ],
                        "nautobot_identifier": "aa1db811-16d8-4a56-ab59-b23bf7b920aa",
                        "!create_or_update:name": "United States",
                    }
                ],
                "nautobot_identifier": "d982ed3b-66ae-4aca-bc6e-0215f57f3b9c",
                "!create_or_update:name": "Americas",
            },
            "device_roles": [
                {
                    "slug": "core_router",
                    "color": "3f51b5",
                    "nautobot_identifier": "7f0e8caf-4c3d-4348-8576-ce8bfa0d6a9e",
                    "!create_or_update:name": "Core Router",
                }
            ],
            "device_types": [
                {
                    "slug": "ptx10016",
                    "u_height": 21,
                    "manufacturer__slug": "juniper",
                    "nautobot_identifier": "44c91fff-548a-401e-8a26-24350ddeff66",
                    "!create_or_update:model": "PTX10016",
                }
            ],
            "manufacturers": [
                {
                    "slug": "juniper",
                    "nautobot_identifier": "e763f36f-ce4b-4096-b160-5d03cd8f8915",
                    "!create_or_update:name": "Juniper",
                }
            ],
        }
        goal_design = {
            "manufacturers": [],
            "device_types": [],
            "device_roles": [],
            "regions": {
                "children": [
                    {
                        "children": [
                            {
                                "sites": [
                                    {
                                        "!ref": "iad5",
                                        "status__name": "Active",
                                        "nautobot_identifier": "a45b4b25-1e78-4c7b-95ad-b2880143cc19",
                                        "!create_or_update:name": "IAD5",
                                    },
                                    {
                                        "!ref": "lga1",
                                        "status__name": "Active",
                                        "nautobot_identifier": "70232953-55f0-41c9-b5bb-bc23d6d88906",
                                        "!create_or_update:name": "LGA1",
                                    },
                                ],
                                "nautobot_identifier": "76a1c915-7b30-426b-adef-9721fb768fce",
                                "!create_or_update:name": "US-East-1",
                            },
                            {
                                "sites": [
                                    {
                                        "!ref": "lax11",
                                        "status__name": "Active",
                                        "nautobot_identifier": "5482d5c6-e4f7-4577-b3c0-50a396872f14",
                                        "!create_or_update:name": "LAX11",
                                    },
                                    {
                                        "!ref": "sea1",
                                        "status__name": "Active",
                                        "nautobot_identifier": "618d24ac-6ccf-4f86-a0bd-c3e816cc9919",
                                        "!create_or_update:name": "SEA1",
                                    },
                                ],
                                "nautobot_identifier": "28a13a4a-9b08-4407-b407-c094d19eaf68",
                                "!create_or_update:name": "US-West-1",
                            },
                        ],
                        "nautobot_identifier": "aa1db811-16d8-4a56-ab59-b23bf7b920aa",
                        "!create_or_update:name": "United States",
                    }
                ],
                "nautobot_identifier": "d982ed3b-66ae-4aca-bc6e-0215f57f3b9c",
                "!create_or_update:name": "Americas",
            },
            "devices": [
                {
                    "site": "!ref:iad5",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "ff4bb89f-972b-4b86-9055-a6a8291703b0",
                    "!create_or_update:name": "core0.iad5",
                },
                {
                    "site": "!ref:lga1",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "d2c289ed-e1c2-4643-a5bc-0768fa037b2d",
                    "!create_or_update:name": "core0.lga1",
                },
                {
                    "site": "!ref:lax11",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "503452bf-54b1-472b-846e-dc0bb5b42f67",
                    "!create_or_update:name": "core0.lax11",
                },
                {
                    "site": "!ref:sea1",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "d5b6ae22-c32c-4722-a350-254ff2caad18",
                    "!create_or_update:name": "core0.sea1",
                },
                {
                    "!create_or_update:name": "core1.iad5",
                    "site": "!ref:iad5",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
                {
                    "!create_or_update:name": "core1.lga1",
                    "site": "!ref:lga1",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
                {
                    "!create_or_update:name": "core1.lax11",
                    "site": "!ref:lax11",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
                {
                    "!create_or_update:name": "core1.sea1",
                    "site": "!ref:sea1",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
            ],
        }
        goal_elements_to_be_decommissioned = {}
        elements_to_be_decommissioned = {}
        future_design = copy.deepcopy(design)
        ext_keys_to_be_simplified = []
        for key, new_value in design.items():
            old_value = previous_design[key]
            future_value = future_design[key]
            to_delete = reduce_design(new_value, old_value, future_value, elements_to_be_decommissioned, key)
            if to_delete:
                ext_keys_to_be_simplified.append(key)

        for key, value in goal_design.items():
            self.assertEqual(value, design[key])

        for key, value in goal_elements_to_be_decommissioned.items():
            self.assertEqual(value, elements_to_be_decommissioned[key])

    def test_reduce_design_3(self):
        design = {
            "vrfs": [{"!create_or_update:name": "64501:2", "description": "VRF for customer xyz", "!ref": "my_vrf"}],
            "prefixes": [
                {"!create_or_update:prefix": "192.0.2.0/24", "status__name": "Reserved"},
                {
                    "!create_or_update:prefix": "192.0.2.0/30",
                    "status__name": "Reserved",
                    "vrf": "!ref:my_vrf",
                    "description": "ertewr",
                },
            ],
            "devices": [
                {
                    "!update:name": "core0.sea1",
                    "local_context_data": {"mpls_router": True},
                    "interfaces": [
                        {
                            "!create_or_update:name": "GigabitEthernet1/1",
                            "status__name": "Planned",
                            "type": "other",
                            "description": "ertewr",
                            "ip_addresses": [{"!create_or_update:address": "192.0.2.1/30", "status__name": "Reserved"}],
                        }
                    ],
                },
                {
                    "!update:name": "core0.iad5",
                    "local_context_data": {"mpls_router": True},
                    "interfaces": [
                        {
                            "!create_or_update:name": "GigabitEthernet1/1",
                            "status__name": "Planned",
                            "type": "other",
                            "description": "ertewr",
                            "ip_addresses": [{"!create_or_update:address": "192.0.2.2/30", "status__name": "Reserved"}],
                        }
                    ],
                },
            ],
        }
        previous_design = {
            "vrfs": [
                {
                    "!ref": "my_vrf",
                    "description": "VRF for customer abc",
                    "nautobot_identifier": "d34f89aa-0199-4352-aa2f-311203bae138",
                    "!create_or_update:name": "64501:1",
                }
            ],
            "devices": [
                {
                    "interfaces": [
                        {
                            "type": "other",
                            "description": "ertewr",
                            "ip_addresses": [
                                {
                                    "status__name": "Reserved",
                                    "nautobot_identifier": "ceaabdd5-811a-4981-aa83-c2c2ff52b081",
                                    "!create_or_update:address": "192.0.2.1/30",
                                }
                            ],
                            "status__name": "Planned",
                            "nautobot_identifier": "0d95bbfc-4438-42e8-b24c-d5d878dd0880",
                            "!create_or_update:name": "GigabitEthernet1/1",
                        }
                    ],
                    "!update:name": "core0.lax11",
                    "local_context_data": {"mpls_router": True},
                    "nautobot_identifier": "c8454078-d3d7-4243-a07f-99750d06c595",
                },
                {
                    "interfaces": [
                        {
                            "type": "other",
                            "description": "ertewr",
                            "ip_addresses": [
                                {
                                    "status__name": "Reserved",
                                    "nautobot_identifier": "bb27bc76-2973-42db-8e6d-5f79e1aecf92",
                                    "!create_or_update:address": "192.0.2.2/30",
                                }
                            ],
                            "status__name": "Planned",
                            "nautobot_identifier": "4506fe8d-71a9-445e-9bf6-7127e84a3d22",
                            "!create_or_update:name": "GigabitEthernet1/1",
                        }
                    ],
                    "!update:name": "core0.iad5",
                    "local_context_data": {"mpls_router": True},
                    "nautobot_identifier": "d14133b0-85dd-440b-99e8-4410078df052",
                },
            ],
            "prefixes": [
                {
                    "status__name": "Reserved",
                    "nautobot_identifier": "22a1b725-a371-4130-8b2b-6b95b9b913ae",
                    "!create_or_update:prefix": "192.0.2.0/24",
                },
                {
                    "vrf": "!ref:my_vrf",
                    "description": "ertewr",
                    "status__name": "Reserved",
                    "nautobot_identifier": "180df48c-7c39-4da2-ac18-6f335cbd2a0e",
                    "!create_or_update:prefix": "192.0.2.0/30",
                },
            ],
        }
        goal_design = {
            "vrfs": [{"!create_or_update:name": "64501:2", "description": "VRF for customer xyz", "!ref": "my_vrf"}],
            "prefixes": [
                {
                    "vrf": "!ref:my_vrf",
                    "description": "ertewr",
                    "status__name": "Reserved",
                    "nautobot_identifier": "180df48c-7c39-4da2-ac18-6f335cbd2a0e",
                    "!create_or_update:prefix": "192.0.2.0/30",
                },
            ],
            "devices": [
                {
                    "!update:name": "core0.sea1",
                    "local_context_data": {"mpls_router": True},
                    "interfaces": [
                        {
                            "!create_or_update:name": "GigabitEthernet1/1",
                            "status__name": "Planned",
                            "type": "other",
                            "description": "ertewr",
                            "ip_addresses": [{"!create_or_update:address": "192.0.2.1/30", "status__name": "Reserved"}],
                        }
                    ],
                }
            ],
        }
        goal_elements_to_be_decommissioned = {
            "vrfs": [("d34f89aa-0199-4352-aa2f-311203bae138", "64501:1")],
            "devices": [("c8454078-d3d7-4243-a07f-99750d06c595", "core0.lax11")],
            "interfaces": [("0d95bbfc-4438-42e8-b24c-d5d878dd0880", "GigabitEthernet1/1")],
            "ip_addresses": [("ceaabdd5-811a-4981-aa83-c2c2ff52b081", "192.0.2.1/30")],
        }
        elements_to_be_decommissioned = {}
        future_design = copy.deepcopy(design)
        ext_keys_to_be_simplified = []
        for key, new_value in design.items():
            old_value = previous_design[key]
            future_value = future_design[key]
            to_delete = reduce_design(new_value, old_value, future_value, elements_to_be_decommissioned, key)
            if to_delete:
                ext_keys_to_be_simplified.append(key)

        for key, value in goal_design.items():
            self.assertEqual(value, design[key])

        for key, value in goal_elements_to_be_decommissioned.items():
            self.assertEqual(value, elements_to_be_decommissioned[key])

    def test_reduce_design_4(self):
        design = {
            "manufacturers": [{"!create_or_update:name": "Juniper", "slug": "juniper"}],
            "device_types": [
                {
                    "!create_or_update:model": "PTX10016",
                    "slug": "ptx10016",
                    "manufacturer__slug": "juniper",
                    "u_height": 21,
                }
            ],
            "device_roles": [{"!create_or_update:name": "Core Router", "slug": "core_router", "color": "3f51b5"}],
            "regions": {
                "!create_or_update:name": "Americas",
                "children": [
                    {
                        "!create_or_update:name": "United States",
                        "children": [
                            {
                                "!create_or_update:name": "US-East-1",
                                "sites": [
                                    {"!create_or_update:name": "IAD5", "status__name": "Active", "!ref": "iad5"},
                                    {"!create_or_update:name": "LGA1", "status__name": "Active", "!ref": "lga1"},
                                ],
                            },
                            {
                                "!create_or_update:name": "US-West-1",
                                "sites": [
                                    {"!create_or_update:name": "LAX11", "status__name": "Active", "!ref": "lax11"},
                                    {"!create_or_update:name": "SEA1", "status__name": "Active", "!ref": "sea1"},
                                ],
                            },
                        ],
                    }
                ],
            },
            "devices": [
                {
                    "!create_or_update:name": "core0.iad5",
                    "site": "!ref:iad5",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
                {
                    "!create_or_update:name": "core0.lga1",
                    "site": "!ref:lga1",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
                {
                    "!create_or_update:name": "core0.lax11",
                    "site": "!ref:lax11",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
                {
                    "!create_or_update:name": "core0.sea1",
                    "site": "!ref:sea1",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                },
            ],
        }
        previous_design = {
            "devices": [
                {
                    "site": "!ref:iad5",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "7d90ac27-3444-4c48-9669-4745c0fe4ffa",
                    "!create_or_update:name": "core0.iad5",
                },
                {
                    "site": "!ref:lga1",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "0a9382a4-6cb0-4fa7-834a-0ea9fba1a825",
                    "!create_or_update:name": "core0.lga1",
                },
                {
                    "site": "!ref:lax11",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "2d3c1d1a-df00-4f0e-bc3c-8899f12ab2cd",
                    "!create_or_update:name": "core0.lax11",
                },
                {
                    "site": "!ref:sea1",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "faa7b89b-a0da-4516-8c75-6d485288f08d",
                    "!create_or_update:name": "core0.sea1",
                },
                {
                    "site": "!ref:iad5",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "6bb2e900-b53d-43df-9a88-048ab7c05bd0",
                    "!create_or_update:name": "core1.iad5",
                },
                {
                    "site": "!ref:lga1",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "d96aadd6-489c-41e6-b9eb-7f3dc7e7c197",
                    "!create_or_update:name": "core1.lga1",
                },
                {
                    "site": "!ref:lax11",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "7ecaca00-65e0-4214-a89d-8560002c4e87",
                    "!create_or_update:name": "core1.lax11",
                },
                {
                    "site": "!ref:sea1",
                    "status__name": "Planned",
                    "device_role__slug": "core_router",
                    "device_type__slug": "ptx10016",
                    "nautobot_identifier": "dd3811ad-158e-464e-8629-0a3cd18aabf0",
                    "!create_or_update:name": "core1.sea1",
                },
            ],
            "regions": {
                "children": [
                    {
                        "children": [
                            {
                                "sites": [
                                    {
                                        "!ref": "iad5",
                                        "status__name": "Active",
                                        "nautobot_identifier": "cf3c08fe-11b7-45b0-9aab-09f8df7bfc89",
                                        "!create_or_update:name": "IAD5",
                                    },
                                    {
                                        "!ref": "lga1",
                                        "status__name": "Active",
                                        "nautobot_identifier": "4eef1fe2-d519-4c9d-ad45-feb04cdcba57",
                                        "!create_or_update:name": "LGA1",
                                    },
                                ],
                                "nautobot_identifier": "0a43260d-0a95-4f2e-93d0-3ecef49069ef",
                                "!create_or_update:name": "US-East-1",
                            },
                            {
                                "sites": [
                                    {
                                        "!ref": "lax11",
                                        "status__name": "Active",
                                        "nautobot_identifier": "8d1ed8a1-b503-49e5-99f4-20140f7cd255",
                                        "!create_or_update:name": "LAX11",
                                    },
                                    {
                                        "!ref": "sea1",
                                        "status__name": "Active",
                                        "nautobot_identifier": "6118a8a4-332a-4b04-a0d6-57170ee0e475",
                                        "!create_or_update:name": "SEA1",
                                    },
                                ],
                                "nautobot_identifier": "2889485e-6222-4634-9f86-bff0afd90939",
                                "!create_or_update:name": "US-West-1",
                            },
                        ],
                        "nautobot_identifier": "da9b46cd-1fc1-4d7b-b5e2-cf382df02b3b",
                        "!create_or_update:name": "United States",
                    }
                ],
                "nautobot_identifier": "e7540dd8-7079-4b25-ad10-8681dd64a69f",
                "!create_or_update:name": "Americas",
            },
            "device_roles": [
                {
                    "slug": "core_router",
                    "color": "3f51b5",
                    "nautobot_identifier": "d121e76b-3882-4224-8087-c41d38ef2257",
                    "!create_or_update:name": "Core Router",
                }
            ],
            "device_types": [
                {
                    "slug": "ptx10016",
                    "u_height": 21,
                    "manufacturer__slug": "juniper",
                    "nautobot_identifier": "44f11fae-b5d2-480f-a8e0-36a3ff06f09a",
                    "!create_or_update:model": "PTX10016",
                }
            ],
            "manufacturers": [
                {
                    "slug": "juniper",
                    "nautobot_identifier": "f50e67d8-1d31-4ec7-a59e-2435cda9870b",
                    "!create_or_update:name": "Juniper",
                }
            ],
        }
        goal_design = {
            "manufacturers": [],
            "device_types": [],
            "device_roles": [],
            "regions": {
                "!create_or_update:name": "Americas",
                "children": [
                    {
                        "!create_or_update:name": "United States",
                        "children": [
                            {
                                "!create_or_update:name": "US-East-1",
                                "sites": [
                                    {
                                        "!create_or_update:name": "IAD5",
                                        "status__name": "Active",
                                        "!ref": "iad5",
                                        "nautobot_identifier": "cf3c08fe-11b7-45b0-9aab-09f8df7bfc89",
                                    },
                                    {
                                        "!create_or_update:name": "LGA1",
                                        "status__name": "Active",
                                        "!ref": "lga1",
                                        "nautobot_identifier": "4eef1fe2-d519-4c9d-ad45-feb04cdcba57",
                                    },
                                ],
                                "nautobot_identifier": "0a43260d-0a95-4f2e-93d0-3ecef49069ef",
                            },
                            {
                                "!create_or_update:name": "US-West-1",
                                "sites": [
                                    {
                                        "!create_or_update:name": "LAX11",
                                        "status__name": "Active",
                                        "!ref": "lax11",
                                        "nautobot_identifier": "8d1ed8a1-b503-49e5-99f4-20140f7cd255",
                                    },
                                    {
                                        "!create_or_update:name": "SEA1",
                                        "status__name": "Active",
                                        "!ref": "sea1",
                                        "nautobot_identifier": "6118a8a4-332a-4b04-a0d6-57170ee0e475",
                                    },
                                ],
                                "nautobot_identifier": "2889485e-6222-4634-9f86-bff0afd90939",
                            },
                        ],
                        "nautobot_identifier": "da9b46cd-1fc1-4d7b-b5e2-cf382df02b3b",
                    }
                ],
                "nautobot_identifier": "e7540dd8-7079-4b25-ad10-8681dd64a69f",
            },
            "devices": [
                {
                    "!create_or_update:name": "core0.iad5",
                    "site": "!ref:iad5",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                    "nautobot_identifier": "7d90ac27-3444-4c48-9669-4745c0fe4ffa",
                },
                {
                    "!create_or_update:name": "core0.lga1",
                    "site": "!ref:lga1",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                    "nautobot_identifier": "0a9382a4-6cb0-4fa7-834a-0ea9fba1a825",
                },
                {
                    "!create_or_update:name": "core0.lax11",
                    "site": "!ref:lax11",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                    "nautobot_identifier": "2d3c1d1a-df00-4f0e-bc3c-8899f12ab2cd",
                },
                {
                    "!create_or_update:name": "core0.sea1",
                    "site": "!ref:sea1",
                    "device_type__slug": "ptx10016",
                    "device_role__slug": "core_router",
                    "status__name": "Planned",
                    "nautobot_identifier": "faa7b89b-a0da-4516-8c75-6d485288f08d",
                },
            ],
        }
        goal_elements_to_be_decommissioned = {
            "devices": [
                ("6bb2e900-b53d-43df-9a88-048ab7c05bd0", "core1.iad5"),
                ("d96aadd6-489c-41e6-b9eb-7f3dc7e7c197", "core1.lga1"),
                ("7ecaca00-65e0-4214-a89d-8560002c4e87", "core1.lax11"),
                ("dd3811ad-158e-464e-8629-0a3cd18aabf0", "core1.sea1"),
            ],
        }
        elements_to_be_decommissioned = {}
        future_design = copy.deepcopy(design)
        ext_keys_to_be_simplified = []
        for key, new_value in design.items():
            old_value = previous_design[key]
            future_value = future_design[key]
            to_delete = reduce_design(new_value, old_value, future_value, elements_to_be_decommissioned, key)
            if to_delete:
                ext_keys_to_be_simplified.append(key)

        for key, value in goal_design.items():
            self.assertEqual(value, design[key])

        for key, value in goal_elements_to_be_decommissioned.items():
            self.assertEqual(value, elements_to_be_decommissioned[key])

    def test_reduce_design_5(self):
        design = {
            "vrfs": [{"!create_or_update:name": "64501:1", "description": "VRF for customer abc", "!ref": "my_vrf"}],
            "prefixes": [
                {"!create_or_update:prefix": "192.0.2.0/24", "status__name": "Reserved"},
                {
                    "!create_or_update:prefix": "192.0.2.0/30",
                    "status__name": "Reserved",
                    "vrf": "!ref:my_vrf",
                    "description": "sadfasd",
                },
            ],
            "devices": [
                {
                    "!update:name": "core1.lax11",
                    "local_context_data": {"mpls_router": True},
                    "interfaces": [
                        {
                            "!create_or_update:name": "GigabitEthernet1/1",
                            "status__name": "Planned",
                            "type": "other",
                            "description": "sadfasd",
                            "ip_addresses": [{"!create_or_update:address": "192.0.2.1/30", "status__name": "Reserved"}],
                        }
                    ],
                },
                {
                    "!update:name": "core0.lax11",
                    "local_context_data": {"mpls_router": True},
                    "interfaces": [
                        {
                            "!create_or_update:name": "GigabitEthernet1/1",
                            "status__name": "Planned",
                            "type": "other",
                            "description": "sadfasd",
                            "!connect_cable": {
                                "status__name": "Planned",
                                "to": {"device__name": "core1.lax11", "name": "GigabitEthernet1/1"},
                            },
                            "ip_addresses": [{"!create_or_update:address": "192.0.2.2/30", "status__name": "Reserved"}],
                        }
                    ],
                },
            ],
        }
        previous_design = {
            "vrfs": [
                {
                    "!ref": "my_vrf",
                    "description": "VRF for customer abc",
                    "nautobot_identifier": "4757e7e5-2362-4199-adee-20cfa1a5b2fc",
                    "!create_or_update:name": "64501:1",
                }
            ],
            "devices": [
                {
                    "interfaces": [
                        {
                            "type": "other",
                            "description": "sadfasd",
                            "ip_addresses": [
                                {
                                    "status__name": "Reserved",
                                    "nautobot_identifier": "8f9a5073-2975-4b9a-86d1-ebe54e73ca6c",
                                    "!create_or_update:address": "192.0.2.1/30",
                                }
                            ],
                            "status__name": "Planned",
                            "nautobot_identifier": "b95378bd-5580-4eeb-9542-c298e8424399",
                            "!create_or_update:name": "GigabitEthernet1/1",
                        }
                    ],
                    "!update:name": "core1.lax11",
                    "local_context_data": {"mpls_router": True},
                    "nautobot_identifier": "aee92e54-4763-4d76-9390-b3a714931a47",
                },
                {
                    "interfaces": [
                        {
                            "type": "other",
                            "description": "sadfasd",
                            "ip_addresses": [
                                {
                                    "status__name": "Reserved",
                                    "nautobot_identifier": "053289c3-1469-4682-9b95-9e499b8563fb",
                                    "!create_or_update:address": "192.0.2.2/30",
                                }
                            ],
                            "status__name": "Planned",
                            "!connect_cable": {
                                "to": {"name": "GigabitEthernet1/1", "device__name": "core1.lax11"},
                                "status__name": "Planned",
                                "nautobot_identifier": "36f26409-5d65-4b50-8934-111f9aafa9ec",
                            },
                            "nautobot_identifier": "30b6689c-8ca6-47d0-8dbe-9c1d300860a6",
                            "!create_or_update:name": "GigabitEthernet1/1",
                        }
                    ],
                    "!update:name": "core0.iad5",
                    "local_context_data": {"mpls_router": True},
                    "nautobot_identifier": "a46729d6-6e71-4905-9833-24dd7841f98a",
                },
            ],
            "prefixes": [
                {
                    "status__name": "Reserved",
                    "nautobot_identifier": "7909ae9d-02de-4034-9ef9-12e1499bc563",
                    "!create_or_update:prefix": "192.0.2.0/24",
                },
                {
                    "vrf": "!ref:my_vrf",
                    "description": "sadfasd",
                    "status__name": "Reserved",
                    "nautobot_identifier": "05540529-6ade-417c-88af-a9b1f4ae75f7",
                    "!create_or_update:prefix": "192.0.2.0/30",
                },
            ],
        }
        goal_design = {
            "vrfs": [
                {
                    "!create_or_update:name": "64501:1",
                    "description": "VRF for customer abc",
                    "!ref": "my_vrf",
                    "nautobot_identifier": "4757e7e5-2362-4199-adee-20cfa1a5b2fc",
                }
            ],
            "prefixes": [
                {
                    "!create_or_update:prefix": "192.0.2.0/30",
                    "status__name": "Reserved",
                    "vrf": "!ref:my_vrf",
                    "description": "sadfasd",
                    "nautobot_identifier": "05540529-6ade-417c-88af-a9b1f4ae75f7",
                }
            ],
            "devices": [
                {
                    "!update:name": "core0.lax11",
                    "local_context_data": {"mpls_router": True},
                    "interfaces": [
                        {
                            "!create_or_update:name": "GigabitEthernet1/1",
                            "status__name": "Planned",
                            "type": "other",
                            "description": "sadfasd",
                            "!connect_cable": {
                                "nautobot_identifier": "36f26409-5d65-4b50-8934-111f9aafa9ec",
                                "status__name": "Planned",
                                "to": {"device__name": "core1.lax11", "name": "GigabitEthernet1/1"},
                            },
                            "ip_addresses": [{"!create_or_update:address": "192.0.2.2/30", "status__name": "Reserved"}],
                        }
                    ],
                }
            ],
        }
        goal_elements_to_be_decommissioned = {
            "interfaces": [("30b6689c-8ca6-47d0-8dbe-9c1d300860a6", "GigabitEthernet1/1")],
            "ip_addresses": [("053289c3-1469-4682-9b95-9e499b8563fb", "192.0.2.2/30")],
            "devices": [("a46729d6-6e71-4905-9833-24dd7841f98a", "core0.iad5")],
        }
        elements_to_be_decommissioned = {}
        future_design = copy.deepcopy(design)
        ext_keys_to_be_simplified = []
        for key, new_value in design.items():
            old_value = previous_design[key]
            future_value = future_design[key]
            to_delete = reduce_design(new_value, old_value, future_value, elements_to_be_decommissioned, key)
            if to_delete:
                ext_keys_to_be_simplified.append(key)

        for key, value in goal_design.items():
            self.assertEqual(value, design[key])

        for key, value in goal_elements_to_be_decommissioned.items():
            self.assertEqual(value, elements_to_be_decommissioned[key])


if __name__ == "__main__":
    unittest.main()
