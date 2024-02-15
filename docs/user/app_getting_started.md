# Getting Started with the App

This document provides a step-by-step tutorial on how to get the App going and how to use it.

## Install the App

To install the App, please follow the instructions detailed in the [Installation Guide](../admin/install.md).

## First steps with the App

The easiest way to experience Design Builder is to either add the [demo-designs](https://github.com/nautobot/demo-designs) as a git data source in an existing Nautobot environment, or to clone that repository and run it in a local environment. To start a local environment, clone the [demo-designs](https://github.com/nautobot/demo-designs) git repository and start the application stack. The only requirements for starting a local environment are `docker`, `docker-compose` and [invoke](https://www.pyinvoke.org/installing.html). Once the dependent tools have been installed you'll need to build the docker image by running `invoke build`. At that point, simply run the command `invoke start`. This will start the entire application stack using docker compose. Once the application stack is up and running, navigate to <http://127.0.0.1:8080/> and login. By default, the application stack will use Nautobot version 1.6. To see design builder in Nautobot 2, copy the `invoke.nautobot_2.yml` to `invoke.yml` and restart the application stack.

## What are the next steps?

The Design Builder demo designs ship with some sample designs to demonstrate capabilities. Once the application stack is ready, you should have several jobs listed under the "Jobs" -> "Jobs" menu item.

![Jobs list](../images/screenshots/sample-design-jobs-list.png)

Note that the jobs are disabled. Nautobot automatically marks jobs as disabled when they are first loaded. In order to run these jobs, click the edit button ![edit button](../images/screenshots/edit-button.png) and check the "enabled" checkbox:

![enabled checkbox](../images/screenshots/job-enabled-checkbox.png)

Once you click `save`, the jobs should be runnable.

To implement any design, click the run button [run button](../images/screenshots/run-button.png). For example, run the "Initial Data" job, which will add a manufacturer, a device type, a device role, several regions and several sites. Additionally, each site will have two devices. If you run the job you should see output in the job result that shows the various objects being created:

![design job result](../images/screenshots/design-job-result.png)

Once the initial data job has been run, try enabling and running the "Backbone Site Design" job to create a new site with racks and routers.
