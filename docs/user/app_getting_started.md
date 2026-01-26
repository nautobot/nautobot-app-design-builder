# Getting Started with the App

This document provides a step-by-step tutorial on how to get the App going and how to use it.

## Install the App

To install the App, please follow the instructions detailed in the [Installation Guide](../admin/install.md).

## First steps with the App

The easiest way to experience Design Builder is to either add the [demo-designs](https://github.com/nautobot/demo-designs) as a git data source in an existing Nautobot environment, or in your local [development environment](../dev/dev_environment.md). 

The Design Builder demo designs ship with some sample designs to demonstrate capabilities. Once the application stack is ready, you should have several jobs listed under the "Jobs" -> "Jobs" menu item.

<!-- updated-images -->
![Jobs list](../images/screenshots/sample-design-jobs-list-light.png#only-light){ .on-glb }
![Jobs list](../images/screenshots/sample-design-jobs-list-dark.png#only-dark){ .on-glb }

Note that the jobs are disabled. Nautobot automatically marks jobs as disabled when they are first loaded. In order to run these jobs, click the edit button ![edit button](../images/screenshots/edit-button-light.png#only-light){ .on-glb } ![edit button](../images/screenshots/edit-button-dark.png#only-dark){ .on-glb }  and check the "enabled" checkbox:

<!-- updated-images -->
![enabled checkbox](../images/screenshots/job-enabled-checkbox-light.png#only-light){ .on-glb }
![enabled checkbox](../images/screenshots/job-enabled-checkbox-dark.png#only-dark){ .on-glb }

Once you click `save`, the jobs should be runnable.

To implement any design, click the run button ![run button](../images/screenshots/run-button-light.png#only-light){ .on-glb }![run button](../images/screenshots/run-button-dark.png#only-dark){ .on-glb }. For example, run the "Initial Data" job, which will add a manufacturer, a device type, a device role, several regions and several sites. Additionally, each site will have two devices. If you run the job you should see output in the job result that shows the various objects being created:

<!-- updated-images -->
![design job result](../images/screenshots/design-job-result-light.png#only-light){ .on-glb }
![design job result](../images/screenshots/design-job-result-dark.png#only-dark){ .on-glb }

Once the initial data job has been run, try enabling and running the "Backbone Site Design" job to create a new site with racks and routers.
