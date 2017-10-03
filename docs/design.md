# Design

## Overview
An [Ansible Playbook Bundle (APB)](https://github.com/fusor/ansible-playbook-bundle)
borrows several concepts from the [Nulecule](https://github.com/projectatomic/nulecule)
and the [Atomicapp](http://www.projectatomic.io/docs/atomicapp/) project, namely the concept of a short
lived container with the sole purpose of orchestrating the deployment of the intended application. For the case
of APB, this short lived container is the APB; a container with an Ansible runtime environment
plus any files required to assist in orchestration such as playbooks, roles, and extra dependencies.
Specification of an APB is intended to be lightweight, consisting of several named playbooks and a
metadata file to capture information such as parameters to pass into the application.

## Workflow
APB is broken up into the following steps.

  1. [Preparation](#preparation)
     * [APB init](#apb-initialization)
     * [Spec File](#spec-file)
     * [Actions](#actions) (provision, deprovision, bind, unbind)
  1. [Build](#build)
  1. [Deploy](#deploy)

### Preparation

#### APB Initialization
![Prepare](images/apb-prepare.png)
The first step to creating an APB is to run the `apb init` command, which will create the required skeleton directory structure, and a few required files (e.g. `apb.yml` spec file) for the APB.

##### Directory Structure
The following shows an example directory structure of an APB.
```bash
example-apb/
├── Dockerfile
├── apb.yml
└── roles/
│   └── example-apb-openshift
│       ├── defaults
│       │   └── main.yml
│       └── tasks
│           └── main.yml
└── playbooks/
    └── provision.yml
    └── deprovision.yml
    └── bind.yml
    └── unbind.yml
```

#### Spec File Version 1.0

The `apb init` will create an example APB Spec `apb.yml` File as shown below:
```yml
version: 1.0
name: my-apb
image: <docker-org>/my-apb
description: "My New APB"
bindable: false
async: optional
metadata: {}
plans:
  - name: default
    description: Sample description
    metadata: {}
    parameters: []
```
The spec file will need to be edited for your specific application.

For example, the `etherpad-apb` spec file looks as follows:
```yml
version: 1.0
name: etherpad-apb
image: ansibleplaybookbundle/etherpad-apb
description: Note taking web application
bindable: True
async: optional
metadata: 
  documentationUrl: https://github.com/ether/etherpad-lite/wiki
  imageUrl: https://translatewiki.net/images/thumb/6/6f/Etherpad_lite.svg/200px-Etherpad_lite.svg.png
  dependencies: ['docker.io/mariadb:latest', 'docker.io/tvelocity/etherpad-lite:latest']
  displayName: Etherpad (APB)
  longDescription: An apb that deploys Etherpad Lite
plans:
  - name: default
    description: A single etherpad application with no DB
    free: true
    metadata:
      displayName: Default
      longDescription: This plan provides a single Etherpad application with no database
      cost: $0.00
    parameters:
      - name: mariadb_name
        required: true
        default: etherpad
        type: string
        title: MariaDB Database Name
      - name: mariadb_user
        required: true
        default: etherpad
        title: MariaDB User
        type: string
        maxlength: 63
      - name: mariadb_password
        default: admin
        type: string
        description: A random alphanumeric string if left blank
        title: MariaDB Password
      - name: mariadb_root_password
        default: admin
        type: string
        description: root password for mariadb
        title: Root Password
```

The `metadata` field is optional and used when integrating with the origin service catalog.

APB's with no parameters would define the `parameters` field as follows:
```yml
parameters: []
```

Each item in the `parameters` section can have several fields.  `name` is required.  The order of the parameters will be displayed in sequential order in the form in the OpenShift UI.
```yaml
parameters:
  - name: my_param
    title: My Parameter
    type: enum
    enum: ['X', 'Y', 'Z']
    required: True
    default: X
    display_type: select
    display_group: Group 1
```
* `name`: Unique name of the parameter passed into the APB
* `title`: Displayed label in the UI.
* `type`: Data type of the parameters as specified by [json-schema](http://json-schema.org/) such as `string`, `number`, `int`, `boolean`, or `enum`.  Default input field type in the UI will be assigned if no `display_type` is assigned.
* `required`: Whether or not the parameter is required for APB execution.  Required field in UI.
* `default`: Default value assigned to the parameter.
* `display_type`: Display type for the UI.  For example, you can override a string input as a `password` to hide it in the UI.  Accepted fields include `text`, `textarea`, `password`, `checkbox`, `select`.
* `display_group`: will cause a parameter to display in groups with adjacent parameters with matching `display_group` fields.  In the above example, adding another field below with `display_group: Group 1` will visually group them together in the UI under the heading "Group 1".

#### Actions
The following are the actions for an APB. At a minimum, an APB must implement the `provision` and `deprovision` actions.
 * provision.yml
   * Playbook called to handle installing application to the cluster
 * deprovision.yml
   * Playbook called to handle uninstalling
 * bind.yml
   * Playbook to grant access to another service to use this service, i.e. generates credentials
 * unbind.yml
   * Playbook to revoke access to this service
 * test.yml
   * Playbook to test the the APB is vaild. This is an optional action.

The required named playbooks correspond to methods defined by the [Open Service Broker API](https://github.com/openservicebrokerapi/servicebroker). For example, when the
Ansible Service Broker needs to `provision` an APB it will execute the `provision.yml`.

After the required named playbooks have been generated, the files can be used directly to test management of the
application. A developer may want to work with this directory of files, make tweaks, run, repeat until they are
happy with the behavior. They can test the playbooks by invoking Ansible directly with the playbook and any
required variables.

### Build
The build step is responsible for building a container image from the named playbooks for distribution.
Packaging combines a base image containing an Ansible runtime with Ansible artifacts and any dependencies required
to run the playbooks. The result is a container image with an ENTRYPOINT set to take in several arguments, one of
which is the method to execute, such as provision, deprovision, etc.

![Package](images/apb-package.png)

### Deploy
Deploying an APB means invoking the container and passing in the name of the playbook to execute along with any
required variables. It’s possible to invoke the APB directly without going through the Ansible Service Broker.
Each APB is packaged so it’s ENTRYPOINT will invoke Ansible when run. The container is intended to be short-lived,
coming up to execute the Ansible playbook for managing the application then exiting.

In a typical APB deploy, the APB container will provision an application by running the `provision.yml` playbook
 which executes a deployment role. The deployment role is responsible for creating the OpenShift resources,
 perhaps through calling `oc create` commands or leveraging Ansible modules. The end result is that the APB runs
 Ansible to talk to OpenShift to orchestrate the provisioning of the intended application.

![Deploy](images/apb-deploy.png)
