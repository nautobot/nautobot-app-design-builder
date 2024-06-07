# App Overview

This document provides an overview of the App including critical information and import considerations when applying it to your Nautobot environment.

!!! note
    Throughout this documentation, the terms "app" and "plugin" will be used interchangeably.

## Description

Design Builder provides a system where standardized network designs can be developed to produce or update collections of objects within Nautobot. These designs are text based templates that can create and update hierarchical data structures within Nautobot.

The deployment of a design allows a complete lifecycle management of all the changes connected as a single entity. This means that a design deployment (i.e., a concrete combination of input data with a design) can be updated or decommissioned after its creation, and all the data changes introduced can be enforced even when accessing the data outside of the design builder app.

## Audience (User Personas) - Who should use this App?

- Network engineers who want to have reproducible sets of Nautobot objects based on some standard design.
- Automation engineers who want to be able to automate the creation of Nautobot objects based on a set of standard designs.
- Users who want to leverage abstracted network services defined by network engineers in a simplfied way.
- Network Managers who need a design-driven point of view of the network more abstract than per device. For example, getting the bill of materials (BOM) for a concrete deployment.

## Authors and Maintainers

- Andrew Bates (@abates)
- Mzb (@mzbroch)

## Nautobot Features Used

- This application interacts directly with Nautobot's Object Relational Mapping (ORM) system.
- It uses (optionally) `CustomValidators` and `pre_delete` signals to enforce data protection for existing design deployments.
