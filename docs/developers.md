# Developer Guide

The Service Bundle developer guide provides an in depth guide to creating Bundles. This guide will explain the fundamental components that make up a Service Bundle and is meant to help an experienced Bundle developer get a better understanding of each individual component within a Service Bundle. If you are looking to get more information on creating your first Service Bundle, take a look at our [getting started guide](https://github.com/ansibleplaybookbundle/ansible-playbook-bundle/blob/master/docs/getting_started.md).

  1. [Directory Structure](#directory-structure)
  1. [Explanation of Service Bundle Spec File](#service-bundle-spec-file)
  1. [Dockerfile](#dockerfile)
  1. [Bundle Actions (Playbooks)](#actions)
     * [Binding Credentials](#binding-credentials)
  1. [Working with Common Resources](#working-with-common-resources)
     * [Service](#service)
     * [DeploymentConfig](#deployment-config)
     * [Route](#route)
     * [PersistentVolume](#persistent-volume)
  1. [Custom Error Message](#custom-error-message)
  1. [Tips & Tricks](#tips-and-tricks)
     * [Optional Variables](#optional-variables)
     * [Working with Restricted SCC](#working-with-the-restricted-scc)
     * [Using a ConfigMap](#using-a-configmap-within-a-bundle)
     * [Testing Service Bundles with docker run](#using-docker-run-to-quickly-test-a-bundle)
     * [Developing Bundles for Use in Proxied Environments](#developing-bundles-for-use-in-proxied-environments)
  1. [Service Bundle Spec Version](#service-bundle-spec-versioning)

## Service Bundle Examples

For completed Service Bundle examples, take a look at some of the Bundles in the [ansibleplaybookbundle org](https://github.com/ansibleplaybookbundle)
* [hello-world-apb](https://github.com/ansibleplaybookbundle/hello-world-apb)
* [hello-world-db-apb](https://github.com/ansibleplaybookbundle/hello-world-db-apbb)
* [pyzip-demo-apb](https://github.com/ansibleplaybookbundle/pyzip-demo-apb)
* [pyzip-demo-db-apb](https://github.com/ansibleplaybookbundle/pyzip-demo-db-apb)
* [nginx-apb](https://github.com/ansibleplaybookbundle/nginx-apb)
* [rocketchat-apb](https://github.com/ansibleplaybookbundle/rocketchat-apb)
* [etherpad-apb](https://github.com/ansibleplaybookbundle/etherpad-apb)
* [hastebin-apb](https://github.com/ansibleplaybookbundle/hastebin-apb)
* [mediawiki-apb](https://github.com/ansibleplaybookbundle/mediawiki-apb)
* [jenkins-apb](https://github.com/ansibleplaybookbundle/jenkins-apb)
* [manageiq-apb](https://github.com/ansibleplaybookbundle/manageiq-apb)
* [wordpress-ha-apb](https://github.com/ansibleplaybookbundle/wordpress-ha-apb)
* [thelounge-apb](https://github.com/ansibleplaybookbundle/thelounge-apb)
* [postgresql-apb](https://github.com/ansibleplaybookbundle/postgresql-apb)
* [rhscl-mariadb-apb](https://github.com/ansibleplaybookbundle/rhscl-mariadb-apb)
* [rhscl-mysql-apb](https://github.com/ansibleplaybookbundle/rhscl-mysql-apb)
* [rds-postgres-apb](https://github.com/ansibleplaybookbundle/rds-postgres-apb)
* [kubevirt-apb](https://github.com/ansibleplaybookbundle/kubevirt-apb)

## Directory Structure

The following shows an example directory structure of a Service Bundle.
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

## Service Bundle Spec File

The Service Bundle Spec File (`apb.yml`) is where the outline of your application is declared.  The following is an example Bundle spec

```yaml
version: 1.0
name: example-apb
description: A short description of what this Bundle does
bindable: True
async: optional
metadata:
  documentationUrl: <link to documentation>
  imageUrl: <link to URL of image>
  dependencies: ['<registry>/<organization>/<dependency-name-1>', '<registry>/<organization>/<dependency-name-2>']
  displayName: Example App (APB)
  longDescription: A longer description of what this Bundle does
  providerDisplayName: "Red Hat, Inc."
plans:
  - name: default
    description: A short description of what this plan does
    free: true
    metadata:
      displayName: Default
      longDescription: A longer description of what this plan deploys
      cost: $0.00
    parameters:
      - name: parameter_one
        required: true
        default: foo_string
        type: string
        title: Parameter One
        maxlength: 63
      - name: parameter_two
        required: true
        default: true
        title: Parameter Two
        type: boolean
```

### Top level structure

* `version`: Version of the Bundle spec. Please see [versioning](#apb-spec-versioning) for more information.
* `name`: Name of the Service Bundle. Names must be valid ASCII and may contain lowercase letters, digits, underscores, periods and dashed. Please see [Docker's guidelines](https://docs.docker.com/engine/reference/commandline/tag/#extended-description) for valid tag names.
* `description`: Short description of this Service Bundle.
* `bindable`: Boolean option of whether or not this Service Bundle can be bound to. Accepted fields are `true` or `false`.
* `async`: Field to determine whether the Service Bundle can be deployed asynchronously. Accepted fields are `optional`, `required`, `unsupported`.
* `metadata`: A dictionary field declaring relevant metadata information. Please see the [metadata section](#metadata) for more information.
* `plans`: A list of plans that can be deployed. Please see the [plans section](#plans) for more information.

#### Metadata

* `documentationUrl`: URL to the applications documentation.
* `imageUrl`: URL to an image which will be displayed in the WebUI for the Service Catalog.
* `dependencies`: List of images which are consumed from within the Bundle.
* `displayName`: The name that will be displayed in the WebUI for this Bundle.
* `longDescription`: Longer description that will be displayed when the Bundle is clicked in the WebUI.
* `providerDisplayName`: Name of who is providing this Bundle for consumption.

#### Plans

Plans are declared as a list. This section will explain what each field in a plan describes.

* `name`: Unique name of plan to deploy. This will be displayed when the Bundle is clicked from the Service Catalog.
* `description`: Short description of what will be deployed from this plan.
* `free`: Boolean field to determine if this plan is free or not. Accepted fields are `true` or `false`.
* `metadata`: Dictionary field declaring relevant plan metadata information. Please see the [plan metadata section](#plan-metadata)
* `parameters`: List of parameter dictionaries used as input to the Bundle. Please see the [parameters section](#parameters)

#### Plan Metadata

* `displayName`: Name to display for the plan in the WebUI.
* `longDescription`: Longer description of what this plan deploys.
* `cost`: How much the plan will cost to deploy. Accepted field is `$x.yz`

#### Parameters

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
  - name: param_validate
    title: Parameter with validation
    type: string
    pattern: "^[a-zA-Z_][a-zA-Z0-9_]*$"
    maxlength: 63
```

* `name`: Unique name of the parameter passed into the Bundle
* `title`: Displayed label in the UI.
* `type`: Data type of the parameters as specified by [json-schema](http://json-schema.org/) such as `string`, `number`, `int`, `boolean`, or `enum`.  Default input field type in the UI will be assigned if no `display_type` is assigned.
* `required`: Whether or not the parameter is required for Bundle execution.  Required field in UI.
* `default`: Default value assigned to the parameter.
* `display_type`: Display type for the UI.  For example, you can override a string input as a `password` to hide it in the UI.  Accepted fields include `text`, `textarea`, `password`, `checkbox`, `select`.
* `display_group`: will cause a parameter to display in groups with adjacent parameters with matching `display_group` fields.  In the above example, adding another field below with `display_group: Group 1` will visually group them together in the UI under the heading "Group 1".
* `pattern`: RegEx to be used for parameter validation against strings.
* `maxlength`: Integer value of the max number of characters allowed in the string.

Notice in the above example that the second parameter `param_validate` demonstrates doing RegEx validation on input. This is done with the `pattern` directive and you can also specify the maximum allowable character limit with `maxlength`.

When using a long list of parameters it might be useful to use a shared parameter list. For an example of this, please see [rhscl-postgresql-apb](https://github.com/ansibleplaybookbundle/rhscl-postgresql-apb/blob/master/apb.yml#L4) for an example.

### Kubernetes and Openshift

The Ansible Service Broker is capable of running on both OpenShift and Kubernetes.
Since each runtime uses different ansible modules, the variable ```cluster``` is
used to distinguish between which playbook is run.

In this example provision.yaml, the default playbook is set to Kubernetes, but
the playbook that gets run is determined by ```--extra-vars cluster=<runtime>```:

```yaml
- name: Provisioning app to "{{ cluster }}"
  hosts: localhost
  gather_facts: false
  vars:
    cluster: "kubernetes"
  connection: local
  roles:
  - role: ansible.kubernetes-modules
  - role: ansibleplaybookbundle.asb-modules
  - "{{ cluster }}"
```

For a full example of how this works, see the [mediawiki-apb](https://github.com/ansibleplaybookbundle/mediawiki-apb).

## Dockerfile

The Dockerfile is what's used to actually build the Service Bundle image.  As a result, sometimes you will need to customize it for your own needs.  For example, if running a playbook that requires interactions with PostgreSQL, you may want to install the required packages by adding the `yum install`.

```yaml
FROM ansibleplaybookbundle/apb-base
MAINTAINER Ansible Playbook Bundle Community

LABEL "com.redhat.apb.spec"=\
"<------------base64-encoded-spec------------>"


COPY roles /opt/ansible/roles
COPY playbooks /opt/apb/actions
RUN chmod -R g=u /opt/{ansible,apb}


### INSTALL THE REQUIRED PACKAGES
RUN yum -y install python-boto postgresql && yum clean all

USER apb
```

## Actions

An action for a Service Bundle is the command that the Bundle is run with. 5 standard actions that we support are `provision`, `deprovision`, `bind`, `unbind`, and `test`. For an action to be valid there must be a valid file in the `playbooks` directory named `<action>.yml`. These playbooks can do anything which also means that you can technically create any action you would like. Our [mediawiki-apb](https://github.com/ansibleplaybookbundle/mediawiki123-apb/blob/master/playbooks/update.yml) has an example of creating an action `update`.

Most Bundles will normally have a `provision` to create resources and a `deprovision` action to destroy the resources when deleting the service.

<a id="binding-credentials"></a>

`bind` and `unbind` are used when the coordinates of one service needs to be made available to another service.  This is often the case when creating a data service and making it available to an application.  There are future plans to asynchronously execute `bind` and `unbind` playbooks, but currently, the coordinates are made available during the provision.

To properly make our coordinates available to another service, we use the `asb_encode_binding` module. This module should be called at the end of the Bundle's provision role and it will return bind credentials to the Ansible Service Broker.

```yaml
- name: encode bind credentials
  asb_encode_binding:
    fields:
      EXAMPLE_FIELD: foo
      EXAMPLE_FIELD2: foo2
```

## Working with Common Resources

Below is a list of common resources that are created when developing Service Bundles. Please see the [Ansible Kubernetes Module](https://github.com/ansible/ansible-kubernetes-modules/tree/master/library) for a full list of available resource modules.

### Service

The following is a sample ansible task to create a service named `hello-world`. It is worth noting that the `namespace` variable in a Service Bundle will be provided by the Ansible Service Broker when launched from the WebUI.

* Provision

```yaml
- name: create hello-world service
  k8s_v1_service:
    name: hello-world
    namespace: '{{ namespace }}'
    labels:
      app: hello-world
      service: hello-world
    selector:
      app: hello-world
      service: hello-world
    ports:
      - name: web
        port: 8080
        target_port: 8080
```

* Deprovision

```yaml
- k8s_v1_service:
    name: hello-world
    namespace: '{{ namespace }}'
    state: absent
```

### Deployment Config

The following is a sample ansible task to create a deployment config for the image: `docker.io/ansibleplaybookbundle/hello-world` which maps to service `hello-world`.

* Provision

```yaml
- name: create deployment config
  openshift_v1_deployment_config:
    name: hello-world
    namespace: '{{ namespace }}'
    labels:
      app: hello-world
      service: hello-world
    replicas: 1
    selector:
      app: hello-world
      service: hello-world
    spec_template_metadata_labels:
      app: hello-world
      service: hello-world
    containers:
    - env:
      image: docker.io/ansibleplaybookbundle/hello-world:latest
      name: hello-world
      ports:
      - container_port: 8080
        protocol: TCP
```

* Deprovision

```yaml
- openshift_v1_deployment_config:
    name: hello-world
    namespace: '{{ namespace }}'
    state: absent
```

### Route

The following is an example of creating a route named `hello-world` which maps to service `hello-world`.

* Provision

```yaml
- name: create hello-world route
  openshift_v1_route:
    name: hello-world
    namespace: '{{ namespace }}'
    spec_port_target_port: web
    labels:
      app: hello-world
      service: hello-world
    to_name: hello-world
```

* Deprovision

```yaml
- openshift_v1_route:
    name: hello-world
    namespace: '{{ namespace }}'
    state: absent
```

### Persistent Volume

The following is an example of creating a persistent volume claim resource and deployment config that uses it.

* Provision

```yaml
# Persistent volume resource
- name: create volume claim
  k8s_v1_persistent_volume_claim:
    name: hello-world-db
    namespace: '{{ namespace }}'
    state: present
    access_modes:
      - ReadWriteOnce
    resources_requests:
      storage: 1Gi


# In addition to the resource, we need to add our volume to the deployment config declaration.
# The following is an example deployment config with a persistent volume.
- name: create hello-world-db deployment config
  openshift_v1_deployment_config:
    name: hello-world-db
    ---
    volumes:
    - name: hello-world-db
      persistent_volume_claim:
        claim_name: hello-world-db
      test: false
      triggers:
      - type: ConfigChange
```

* Deprovision

```yaml
- openshift_v1_deployment_config:
    name: hello-world-db
    namespace: '{{ namespace }}'
    state: absent

- k8s_v1_persistent_volume_claim:
    name: hello-world-db
    namespace: '{{ namespace }}'
    state: absent

```

## Tips and Tricks

### Optional Variables

You can add optional variables to an Ansible Playbook Bundle by using environment variables. To pass variables into a Service Bundle, you will need to escape the variable substitution in your `.yml` files. For example, the section below is of [main.yml](https://github.com/fusor/apb-examples/blob/master/etherpad-apb/roles/provision-etherpad-apb/tasks/main.yml#L89) in the [etherpad-apb](https://github.com/fusor/apb-examples/tree/master/etherpad-apb):

```yaml
- name: create mariadb deployment config
  openshift_v1_deployment_config:
    name: mariadb
    namespace: '{{ namespace }}'
    ...
    - env:
      - name: MYSQL_ROOT_PASSWORD
        value: '{{ mariadb_root_password }}'
      - name: MYSQL_DATABASE
        value: '{{ mariadb_name }}'
      - name: MYSQL_USER
        value: '{{ mariadb_user }}'
      - name: MYSQL_PASSWORD
        value: '{{ mariadb_password }}'
```

To define variables, use the `main.yml` file under the `defaults` folder to define/set other variables for your Bundle.  For example, below is the [defaults/main.yml](https://github.com/fusor/apb-examples/blob/master/etherpad-apb/roles/provision-etherpad-apb/defaults/main.yml) for the `etherpad-apb`:

```yaml
playbook_debug: no
mariadb_root_password: "{{ lookup('env','MYSQL_ROOT_PASSWORD') | default('admin', true) }}"
mariadb_name: "{{ lookup('env','MYSQL_DATABASE') | default('etherpad', true) }}"
mariadb_user: "{{ lookup('env','MYSQL_USER') | default('etherpad', true) }}"
mariadb_password: "{{ lookup('env','MYSQL_PASSWORD') | default('admin', true) }}"
etherpad_admin_password: "{{ lookup('env','ETHERPAD_ADMIN_PASSWORD') | default('admin', true) }}"
etherpad_admin_user: "{{ lookup('env','ETHERPAD_ADMIN_USER') | default('etherpad', true) }}"
etherpad_db_host: "{{ lookup('env','ETHERPAD_DB_HOST') | default('mariadb', true) }}"
state: present
```

### Alternative to using `apb push`
When developing Service Bundles, there are a couple of factors which could prevent the developer from using the full development lifecycle that the `apb` tooling offers. Primarily these factors are:
* Developing against an OpenShift/Kubernetes cluster that exists on a remote host
* Developing Bundles on a machine that doesn't have access to the Docker daemon

If a developer meets any of these criteria, then we suggest the following workflow to publish images to the internal OCP registry so that the Automation Broker can bootstrap the image. This section will show you how to do these steps with the `apb` tooling and without.

* Step 1: Ensure the base64 encoded spec is a label in the Dockerfile

This is usually done via `apb prepare`. If you do not have the `apb` tooling installed, you can run:
```
$ cat apb.yml | base64
```
This will return the base64 encoded `apb.yml` which you can copy and paste into the `Dockerfile` under the `LABEL` `com.redhat.apb.spec` like:
```
LABEL "com.redhat.apb.spec"=\
"dmVyc2lvbjogMS4wCm5hbWU6IG1lZGlhd2lraS1hcGIKZGVzY3JpcHRpb246IE1lZGlhd2lraSBh\
cGIgaW1wbGVtZW50YXRpb24KYmluZGFibGU6IEZhbHNlCmFzeW5jOiBvcHRpb25hbAptZXRhZGF0\
YToKICBkb2N1bWVudGF0aW9uVXJsOiBodHRwczovL3d3dy5tZWRpYXdpa2kub3JnL3dpa2kvRG9j\
dW1lbnRhdGlvbgogIGxvbmdEZXNjcmlwdGlvbjogQW4gYXBiIHRoYXQgZGVwbG95cyBNZWRpYXdp\
a2kgMS4yMwogIGRlcGVuZGVuY2llczogWydkb2NrZXIuaW8vYW5zaWJsZXBsYXlib29rYnVuZGxl\
L21lZGlhd2lraTEyMzpsYXRlc3QnXQogIGRpc3BsYXlOYW1lOiBNZWRpYXdpa2kgKEFQQilmZGZk\
CiAgY29uc29sZS5vcGVuc2hpZnQuaW8vaWNvbkNsYXNzOiBpY29uLW1lZGlhd2lraQogIHByb3Zp\
ZGVyRGlzcGxheU5hbWU6ICJSZWQgSGF0LCBJbmMuIgpwbGFuczoKICAtIG5hbWU6IGRlZmF1bHQK\
ICAgIGRlc2NyaXB0aW9uOiBBbiBBUEIgdGhhdCBkZXBsb3lzIE1lZGlhV2lraQogICAgZnJlZTog\
VHJ1ZQogICAgbWV0YWRhdGE6CiAgICAgIGRpc3BsYXlOYW1lOiBEZWZhdWx0CiAgICAgIGxvbmdE\
ZXNjcmlwdGlvbjogVGhpcyBwbGFuIGRlcGxveXMgYSBzaW5nbGUgbWVkaWF3aWtpIGluc3RhbmNl\
IHdpdGhvdXQgYSBEQgogICAgICBjb3N0OiAkMC4wMAogICAgcGFyYW1ldGVyczoKICAgICAgLSBu\
YW1lOiBtZWRpYXdpa2lfZGJfc2NoZW1hCiAgICAgICAgZGVmYXVsdDogbWVkaWF3aWtpCiAgICAg\
ICAgdHlwZTogc3RyaW5nCiAgICAgICAgdGl0bGU6IE1lZGlhd2lraSBEQiBTY2hlbWEKICAgICAg\
ICBwYXR0ZXJuOiAiXlthLXpBLVpfXVthLXpBLVowLTlfXSokIgogICAgICAgIHJlcXVpcmVkOiBU\
cnVlCiAgICAgIC0gbmFtZTogbWVkaWF3aWtpX3NpdGVfbmFtZQogICAgICAgIGRlZmF1bHQ6IE1l\
ZGlhV2lraQogICAgICAgIHR5cGU6IHN0cmluZwogICAgICAgIHRpdGxlOiBNZWRpYXdpa2kgU2l0\
ZSBOYW1lCiAgICAgICAgcGF0dGVybjogIl5bYS16QS1aXSskIgogICAgICAgIHJlcXVpcmVkOiBU\
cnVlCiAgICAgICAgdXBkYXRhYmxlOiBUcnVlCiAgICAgIC0gbmFtZTogbWVkaWF3aWtpX3NpdGVf\
bGFuZwogICAgICAgIGRlZmF1bHQ6IGVuCiAgICAgICAgdHlwZTogc3RyaW5nCiAgICAgICAgdGl0\
bGU6IE1lZGlhd2lraSBTaXRlIExhbmd1YWdlCiAgICAgICAgcGF0dGVybjogIl5bYS16XXsyLDN9\
JCIKICAgICAgICByZXF1aXJlZDogVHJ1ZQogICAgICAtIG5hbWU6IG1lZGlhd2lraV9hZG1pbl91\
c2VyCiAgICAgICAgZGVmYXVsdDogYWRtaW4KICAgICAgICB0eXBlOiBzdHJpbmcKICAgICAgICB0\
aXRsZTogTWVkaWF3aWtpIEFkbWluIFVzZXIgKENhbm5vdCBiZSB0aGUgc2FtZSB2YWx1ZSBhcyBB\
ZG1pbiBVc2VyIFBhc3N3b3JkKQogICAgICAgIHJlcXVpcmVkOiBUcnVlCiAgICAgIC0gbmFtZTog\
bWVkaWF3aWtpX2FkbWluX3Bhc3MKICAgICAgICB0eXBlOiBzdHJpbmcKICAgICAgICB0aXRsZTog\
TWVkaWF3aWtpIEFkbWluIFVzZXIgUGFzc3dvcmQKICAgICAgICByZXF1aXJlZDogVHJ1ZQogICAg\
ICAgIGRpc3BsYXlfdHlwZTogcGFzc3dvcmQK"
```

* Step 2: Populate the internal OCP registry with our built Service Bundle image

This is what is normally handled by `apb push`. In order to build our image without using Docker, we will take advantage of the source-to-image functionality of OpenShift. By default, the Automation Broker is configured to look at the `openshift` namespace for published Service Bundles. The `openshift` namespace is detailed in our documentation as a namespace which exposes its images/imagestreams to be available to any authenticated user on the cluster. We will take advantage of this by using `oc new-app` in namespace `openshift` to build our image.
```
$ oc new-app <path_to_bundle_source> --name <bundle_name> -n openshift
```
After a couple of minutes we should now see our image in the internal registry:
```
$ oc get images | grep <bundle_name>
sha256:b2dcb4b95e178e9b7ac73e5ee0211080c10b24260f76cfec30b89e74e8ee6742   172.30.1.1:5000/openshift/<bundle_name>@sha256:b2dcb4b95e178e9b7ac73e5ee0211080c10b24260f76cfec30b89e74e8ee6742
```

* Step 3: Bootstrap the Automation Broker

This is normally also handled by `apb push` or `apb bootstrap`. I recommend `apb bootstrap` for this step since it will also relist the Service Catalog without you having to wait 5-10 minutes. If you do not have access to do `apb bootstrap`, you can also do the following:
```
$ oc get route -n ansible-service-broker
NAME       HOST/PORT                                           PATH      SERVICES   PORT        TERMINATION   WILDCARD
asb-1338   asb-1338-ansible-service-broker.172.17.0.1.nip.io             asb        port-1338   reencrypt     None

$ curl -H "Authorization: Bearer $(oc whoami -t)" -k -X POST https://asb-1338-ansible-service-broker.172.17.0.1.nip.io/ansible-service-broker/v2/bootstrap                                 
{
  "spec_count": 38,
  "image_count": 109
}
```
Note: `oc whoami -t` should return a token and the logged in user must have permissions that are documented [here](apb_cli.md#access-permissions)

* Step 4: Verify new Service Bundle exists in the Automation Broker

This is normally the functionality of `apb list`. If you do not have access to use `apb list`, you can use the route gathered from step 3 and do:
```
$ curl -H "Authorization: Bearer $(oc whoami -t)" -k https://asb-1338-ansible-service-broker.172.17.0.1.nip.io/ansible-service-broker/v2/catalog
```

You should see a list of all bootstrapped specs and one that is labeled `localregistry-<bundle_name>`. I recommend using `|grep <bundle_name>` to help find it since the output is in JSON.

### Alternative to using `apb run`
Because of the limitations described above, it may be desired for a user to want the same functionality as `apb run` without having to rely on `apb push` being successful. This is because `apb run` implicitly performs `apb push` first before attempting to provision the application. In order to work around this, a user must first follow the above workaround to push their image onto the internal OpenShift registry. Once the image exists, you should be able to see the image with:
```
$ oc get images | grep <bundle_name>
sha256:bfaa73a5e15bf90faec343c7d5f8cc4f952987afdbc3f11a24c54c037528d2ed   172.30.1.1:5000/openshift/<bundle_name>@sha256:bfaa73a5e15bf90faec343c7d5f8cc4f952987afdbc3f11a24c54c037528d2ed
```

Now in order to provision, we can use `oc run` to launch the Bundle:
```
$ oc new-project <target_namespace>
$ oc create serviceaccount apb
$ oc create rolebinding apb --clusterrole=admin --serviceaccount=<target_namespace>:apb
$ oc run <pod_name> \
      --env="POD_NAME=<pod_name>" \
      --env="POD_NAMESPACE=<target_namespace>" \
      --image=172.30.1.1:5000/openshift/<bundle_name> \
      --restart=Never \
      --attach=true \
      --serviceaccount=apb \
      -- <action> -e namespace=<target_namespace> -e cluster=$CLUSTER```
```

### Working with the restricted scc

When building an OpenShift image, it is important that we do not have our application running as the root user when at all possible. When running under the restriced security context, the application image is launched with a random UID. This will cause problems if your application folder is owned by the root user. A good way to work around this is to add a user to the root group and make the application folder owned by the root group. A very good article on how to support Arbitrary User IDs is shown [here](https://docs.openshift.org/latest/creating_images/guidelines.html#openshift-origin-specific-guidelines). The following is a Dockerfile example of a node app running in `/usr/src`. This command would be run after the application is installed in `/usr/src` and the associated environment variables set.

```Dockerfile
ENV USER_NAME=haste \
    USER_UID=1001 \
    HOME=/usr/src

RUN useradd -u ${USER_UID} -r -g 0 -M -d /usr/src -b /usr/src -s /sbin/nologin -c "<username> user" ${USER_NAME} \
               && chown -R ${USER_NAME}:0 /usr/src \
               && chmod -R g=u /usr/src /etc/passwd
USER 1001
```

### Using a ConfigMap within an Service Bundle

There is a temporary workaround we are using to create configmaps from ansible due to a bug in the Ansible modules.

One common use case for ConfigMaps is when the parameters of an Service Bundle will be used within a configuration file of an application or service. The ConfigMap module allows you to mount a ConfigMap into a pod as a volume which can be used to store the config file. This approach allows you to also leverage the power Ansible's `template` module to create a ConfigMap out of Service Bundle paramters. The following is an example of creating a ConfigMap from a jinja template mounted into a pod as a volume.

```yaml
- name: Create hastebin config from template
  template:
    src: config.js.j2
    dest: /tmp/config.js

- name: Create hastebin configmap
  shell: oc create configmap haste-config --from-file=haste-config=/tmp/config.js

---snip

- name: create deployment config
  openshift_v1_deployment_config:
    name: hastebin
    namespace: '{{ namespace }}'
    labels:
      app: hastebin
      service: hastebin
    replicas: 1
    selector:
      app: hastebin
      service: hastebin
    spec_template_metadata_labels:
      app: hastebin
      service: hastebin
    containers:
    - env:
      image: docker.io/dymurray/hastebin:latest
      name: hastebin
      ports:
      - container_port: 7777
        protocol: TCP
      volumeMounts:
        - mountPath: /usr/src/haste-server/config
          name: config
    - env:
      image: docker.io/modularitycontainers/memcached:latest
      name: memcached
      ports:
      - container_port: 11211
        protocol: TCP
    volumes:
      - name: config
        configMap:
          name: haste-config
          items:
            - key: haste-config
              path: config.js

```

### Using docker run to quickly test a Service Bundle

While developing Service Bundles, you may want to quickly test a Bundle without involving the Automation Broker or Service Catalog. This can be accomplished by using a `docker run` command.

Before continuing, run `oc login` and provide credentials for a cluster-admin user. This method of Service Bundle invocation mounts `~/.kube` into the Bundle container for authentication.

The example below shows a generic `docker run` command with placeholders for an `$SB_IMAGE_NAME`, `$ACTION_NAME`, and `extra-vars`.

```bash
docker run --rm --net=host -v $HOME/.kube:/opt/apb/.kube:z -u $UID \
$SB_IMAGE_NAME \
$ACTION_NAME \
--extra-vars 'namespace=sample-namespace' \
--extra-vars 'example_param_1=foo' \
--extra-vars 'example_param_2=bar' \
```

The next example shows a `docker run` command which will perform the `provision` action of the MediaWiki Service Bundle, with necessary values substituted in.

```bash
docker run --rm --net=host -v $HOME/.kube:/opt/apb/.kube:z -u $UID \
docker.io/ansibleplaybookbundle/mediawiki-apb:latest \
provision \
--extra-vars 'namespace=mediawiki' \
--extra-vars 'mediawiki_db_schema=mediawiki' \
--extra-vars 'mediawiki_admin_pass=test' \
--extra-vars 'mediawiki_admin_user=admin' \
--extra-vars 'mediawiki_site_name=Mediawiki'  \
--extra-vars 'mediawiki_site_lang=en'
```

### Developing Bundles for Use in Proxied Environments

The broker will pass its proxy settings to Bundle action pods (e.g. provision, deprovision, bind, unbind, update) as environment variables. We have found that there is little consensus on proxy settings being read from uppercase vs. lowercase environment variables (e.g. http_proxy vs. HTTP_PROXY), so the broker assigns the same values to both within each Bundle action pod, as shown below.

```bash
http_proxy="<http_proxy>:<port>"
https_proxy="<https_proxy>:<port>"
no_proxy="<no_proxy_list>"

HTTP_PROXY="<http_proxy>:<port>"
HTTPS_PROXY="<https_proxy>:<port>"
NO_PROXY="<no_proxy_list>"
```

As a Service Bundle developer, you can access any of these environment variables from an Ansible Playbook using a lookup.

```yaml
set_fact:
  http_proxy: {{ lookup('env', 'http_proxy') }}
  https_proxy: {{ lookup('env', 'https_proxy') }}
  no_proxy: {{ lookup('env', 'no_proxy') }}
```

#### Passing Proxy Settings to Child Pods

  You might want to pass proxy settings through to child pods created by a Bundle action pod. Edit the provision action of your Bundle, navigating to the section defining the deployment config that will be created for the child pod. Copy the Bundle action pod proxy vars to the `env` section of the container definition as shown below.

```yaml
  - openshift_v1_deployment_config:
      name: demo-app
      namespace: '{{ namespace }}'
      containers:
      - name: demo-app
        env:
          - name: http_proxy
            value: "{{ lookup('env','http_proxy') }}"
          - name: https_proxy
            value: "{{ lookup('env','https_proxy') }}"
          - name: no_proxy
            value: "{{ lookup('env','no_proxy') }}"
          - name: HTTP_PROXY
            value: "{{ lookup('env','http_proxy') }}"
          - name: HTTPS_PROXY
            value: "{{ lookup('env','https_proxy') }}"
          - name: NO_PROXY
            value: "{{ lookup('env','no_proxy') }}"
     [...]
```

If more fine-grained control over proxy settings is desired at provision time, consider adding a boolean parameter to `apb.yml` giving the Bundle user control over whether broker proxy settings should pass through to the Bundle's child pods.

```yaml
[...]
parameters:
  - name: proxy_passthrough
    title: Use broker proxy settings
    type: boolean
    default: False
    updatable: True
    required: True
[...]
```

Then, in the Bundle's provision tasks:

```yaml

  - name: Create DC without proxy passthrough
    openshift_v1_deployment_config:
      [...]
      containers:
      - name: demo-app
      [...]
    when: not proxy_passthrough

  - name: Create DC with proxy passthrough
    openshift_v1_deployment_config:
      [...]
      containers:
      - name: demo-app
        env:
          - name: http_proxy
            value: "{{ lookup('env','http_proxy') }}"
          - name: https_proxy
            value: "{{ lookup('env','https_proxy') }}"
          - name: no_proxy
            value: "{{ lookup('env','no_proxy') }}"
          - name: HTTP_PROXY
            value: "{{ lookup('env','http_proxy') }}"
          - name: HTTPS_PROXY
            value: "{{ lookup('env','https_proxy') }}"
          - name: NO_PROXY
            value: "{{ lookup('env','no_proxy') }}"
      [...]
    when: proxy_passthrough
```

## Dashboard URL

In order to set the dashboard URL on the deployed service instance, we developed an Ansible module that will annotate the APB pod with the desired dashboard URL. This is so that an APB developer can set the dashboard URL at the end of the provision tasks. In version 3.10, this is considered an alpha feature. In order to enable it on your APB, you can set the following in `apb.yml`:
```
alpha:
  dashboard_redirect: True
```

This tells the broker that this APB will be using the [asb_dashboard_url](https://github.com/ansibleplaybookbundle/ansible-asb-modules/blob/master/library/asb_dashboard_url.py) Ansible module. The proper way to use this Ansible module is to call `asb_dashboard_url` at the end of your provision tasks like:

```
- asb_dashboard_url:
    dashboard_url:
      "automationbroker.io"
```

## Custom Error Message

A custom error message can be displayed when a failure occurs in the Bundle. This can be achieved by the pod writing out to its *termination log* which is by default `/dev/termination-log`.

When the Bundle fails, the broker will pass the contents of the pod's termination log to the service catalog (if it exists), and the contents of the termination log will be displayed on the WebUI.  If the termination log is empty, a generic error message would be displayed.

The below shows how this can be achieved in a Service Bundle. It captures the task in a `block` and `rescue`:

```yaml
  - block:
      - name: Creating a DC
        openshift_v1_deployment_config:
          [...]
    rescue:
      ####################################
      # Custom Error Message
      ####################################
      - name: Writing Termination Message '/dev/termination-log'
        shell: echo "[Creating a DC Error] - {{ ansible_failed_result.msg }}" > /dev/termination-log

      - fail: msg="[Bundle Failed! - Plan - '{{ _apb_plan_id }}'] "
```

## Service Bundle Spec Versioning

We are using semantic versioning with the format of x.y where x is a major release and y is a minor release.

The current spec version is 1.0.

### Major Version Bump

We will increment the major version whenever an API breaking change is introduced to the Service Bundle spec. Some examples include:

* Introduction/deletion of a required field
* Changing the yaml format
* New features

### Minor Version Bump

We will increment the minor version whenever a non-breaking change is introduced to the Service Bundle spec. Some examples include:

* Introduction/deletion of an optional field
* Spelling change
* Introduction of new options to an existing field
