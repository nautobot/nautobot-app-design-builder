# App Overview

This document provides an overview of the App including critical information and import considerations when applying it to your Nautobot environment.

!!! note
    Throughout this documentation, the terms "app" and "plugin" will be used interchangeably.

## Description

Design Builder provides a system where standardized network designs can be developed to produce or update collections of objects within Nautobot. These designs are text based templates that can create and update hierarchical data structures within Nautobot.

The deployment of a design comes with a complete lifecycle management of all the changes connected as a single entity. Thus, the design deployment can be updated or decommissioned after its creation, and the all the changes introduced can be honored when accessing the data outside of the design builder app.

## Audience (User Personas) - Who should use this App?

- Network engineers who want to have reproducible sets of Nautobot objects based on some standard design.
- Automation engineers who want to be able to automate the creation of Nautobot objects based on a set of standard designs.
- Users who want to leverage abstracted network services defined by network engineers in a simplfied way.

## Authors and Maintainers

- Andrew Bates (@abates)
- Mzb (@mzbroch)

## Nautobot Features Used

This application interacts directly with Nautobot's Object Relational Mapping (ORM) system.
