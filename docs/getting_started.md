# Getting Started

1. [Introduction](#introduction-to-ansible-playbook-bundles-apbs)

2. [Development Environment](#development-environment)

3. [Creating Your First APB](#creating-your-first-apb)
    1. [Init](#using-apb-init)
    2. [Actions](#actions)
        * [Provision](#provision)
        * [Bind](#bind)
        * [Unbind](#unbind)
        * [Deprovision](#deprovision)

4. [More Information](#more-information)

## Introduction to Ansible Playbook Bundles (APBs)

In this tutorial, we'll walk through the creation of some sample APBs.  We will create actions for them to allow provision, deprovision, bind, and unbind.  You can find more information about the design of APBs in the [design doc](https://github.com/fusor/ansible-playbook-bundle/blob/master/docs/design.md).  

*Note:  For the remainder of this tutorial, substitute your own information for items marked in brackets, for example `<host>:<port>` might need to be replaced with `172.17.0.1.nip.io:8443`.*

## Development Environment
Before getting started with APBs, we need to get your system set up to create them.

First, install the APB tools as documented in the [README](https://github.com/fusor/ansible-playbook-bundle/blob/master/README.md#install).  To check, you can run `apb help` and check for a valid response.
```
$ apb help
usage: apb [-h] [--debug] [--project BASE_PATH] {init,help,prepare,build} ...

APB tooling for assisting in building and packaging APBs.

optional arguments:
  -h, --help            show this help message and exit
  --debug               Enable debug output
  --project BASE_PATH, -p BASE_PATH
                        Specify a path to your project. Defaults to CWD.

subcommand:
  {init,help,prepare,build}
    init                Initialize the directory for APB development
    help                Display this help message
    prepare             Prepare an ansible-container project for APB packaging
    build               Build and package APB container
```

Next, create a local development environment with both a [Service Catalog](https://github.com/kubernetes-incubator/service-catalog) and [Ansible Service Broker](https://github.com/fusor/ansible-service-broker).  We will do this using [catasb](https://github.com/fusor/catasb/tree/dev), a collection of scripts which use Ansible to automate the set up of the cluster for you on a local host, ec2, or virtual machines.  The dev branch of this repo is set up for APB development, so we'll need to clone the repo and check out that branch.  For this tutorial we'll be assuming the locally hosted environment which is documented at [https://github.com/fusor/catasb/tree/dev/local](https://github.com/fusor/catasb/blob/dev/local/README.md).  After completing the set up, take note of the OpenShift cluster **host:port** output by the catasb Ansible scripts so you can login using the command line for the remainder of the tutorial.  It will look something like:

```
$ git clone https://github.com/fusor/catasb.git
$ cd catasb/local
$ git checkout dev
$ ./run_setup_local.sh # or ./reset_environment.sh

...

TASK [debug] *********************************************************************************************************************************
ok: [localhost] => {
    "changed": false,
    "msg": [
        "Hostname: <oc-cluster-host>",
        "Next steps:",
        "1) Visit https://apiserver-service-catalog.<oc-cluster-host>",
        "2) Accept the certificate",
        "3) Visit https://<oc-cluster-host>:<oc-cluster-port> for the console",
        "OR",
        "For CLI access:",
        "oc login --insecure-skip-tls-verify <oc-cluster-host>:<oc-cluster-port> -u admin -p admin",
        ""
    ]
}
```

Test out your development environment using [apb-examples](https://github.com/fusor/apb-examples):

```
git clone git@github.com:fusor/apb-examples.git
cd hello-world-apb
apb build
docker build -t <docker-org>/hello-world-apb .
docker run -e "OPENSHIFT_TARGET=https://<oc-cluster-host>:<oc-cluster-port>" -e "OPENSHIFT_USER=admin"  -e "OPENSHIFT_PASS=admin" <docker-org>/hello-world-apb provision --extra-vars 'namespace=my-apb'
docker run \
    -e "OPENSHIFT_TARGET=https://<oc-cluster-host>:<oc-cluster-port>" \
    -e "OPENSHIFT_USER=admin" \
    -e "OPENSHIFT_PASS=admin" \
    <docker-org>/hello-world-apb provision
```
This will deploy a hello-world-apb application to your openshift cluster.  By logging on to your cluster at https://<oc-cluster-host>:<oc-cluster-port>, you can view the project and click on the deployed application.

## Creating your first APB
In this tutorial, we'll create an APB for a containerized [hello world application](https://hub.docker.com/r/ansibleplaybookbundle/hello-world/).  We'll work through a basic APB that will mirror the [hello-world-apb](https://github.com/fusor/apb-examples/tree/master/hello-world-apb) in the [apb-examples](https://github.com/fusor/apb-examples) project.

### Using apb init
Our first task is to create the skeleton for your app using the apb tool.  The command for this is simple:
```
apb init my-apb
```
At this point you will see the following file structure
```
my-apb/
├── apb.yml
├── Dockerfile
├── playbooks
└── roles
```
Two files were created at the root directory, an `apb.yml` and a `Dockerfile`.  These are the minimum required for any APB.  For more information, visit the [design doc](https://github.com/fusor/ansible-playbook-bundle/blob/master/docs/design.md).
```yaml
# apb.yml
name: my-apb
image: <docker-org>/my-apb
description: "My New APB"
bindable: false
async: optional
```
```dockerfile
# Dockerfile
FROM ansibleplaybookbundle/apb-base

LABEL "com.redhat.apb.version"="0.1.0"
LABEL "com.redhat.apb.spec"=\

ADD playbooks /opt/apb/actions
ADD roles /opt/ansible/roles

USER apb
```

At this point we have a fully formed APB that we can build
```
cd my-apb
apb build <docker-org>/my-apb
docker push <docker-org>/my-apb 
```

[TODO]: # (We need this to show up in console UI after doing a broker "curl bootstrap" but this doesn't currently show up from the service catalog although it's listed by the broker.)

Visiting the OpenShift console UI at https://<oc-cluster-host>:<oc-cluster-port> will now display the new Ansible Playbook Bundle named my-apb in the catalog under the **_All_** tab.

### Actions
The brand new APB created in the last section doesn't do very much.  For that, we'll have to add some actions.  The actions supported are [provision](#provision), [deprovision](#deprovision), [bind](#bind), and [unbind](#unbind).  We'll add each of these actions in the following sections.

Before we begin, make sure you're logged in.
```
# substitute your information for <oc-cluster-host>:<oc-cluster-port>
oc login --insecure-skip-tls-verify <oc-cluster-host>:<oc-cluster-port> -u admin -p admin
```

[TODO]: # (change the example yaml so that service/route/dc are all different names to explicitly show the relationships specified by selector, etc)

#### Provision
Using the initialized apb from the last section, we can build and run the provision functionality (substitute your own docker organization name and catasb host/port where appropriate):
<a name="run-provision-cmd">
```
# build the apb image
apb build <docker-org>/my-apb

# run provision task
docker run \
    -e "OPENSHIFT_TARGET=https://<oc-cluster-host>:<oc-cluster-port>" \
    -e "OPENSHIFT_USER=admin" \
    -e "OPENSHIFT_PASS=admin" \
    <docker-org>/my-apb provision \
    --extra-vars 'namespace=my-apb'
```
The environment arguments passed in using the `-e OPENSHIFT_TARGET`, `-e OPENSHIFT_USER`, and `-e OPENSHIFT_PASS`, will be used for the apb container to log in to the OpenShift cluster and are required.  The apb image tag `<docker-org>/my-apb` and action `provision` specify what to do.  The `--extra-vars 'namespace=my-apb'` is used to supply variables to the Ansible playbooks we'll write.  Running the above will output `'provision' NOT IMPLEMENTED`.

To add the provision action, we'll need to add a yaml file `provision.yml` inside the `playbooks` directory.
```
my-apb/
├── apb.yml
├── Dockerfile
├── playbooks
│   └── provision.yml
└── roles
```
`playbooks/provision.yml` is the Ansible playbook that will be run when the **_provision_** action is called from the Ansible Service Broker.  Paste in the following code:
```yaml
- name: provision my-apb
  hosts: localhost
  gather_facts: false
  connection: local
  roles:
  - role: ansible.kubernetes-modules
    install_python_requirements: no
  - role: provision-my-apb
    playbook_debug: false
```

`provision.yml` is a new Ansible playbook which will execute on `localhost` and execute the role `provision-my-apb`.  This playbook works on it's local container created by the service broker.  The `ansible.kubernetes-modules` role will allow us to use the [ansible-kubernetes-modules](https://github.com/ansible/ansible-kubernetes-modules) to create our OpenShift resources.  The `provision-my-apb` doesn't exist yet, but that's where all the work will go when deploying our hello-world app.  Let's create it now.

First, create a new file called `main.yml` inside a `roles/provision-my-apb` directory.
```
mkdir -p roles/provision-my-apb/tasks
touch roles/provision-my-apb/tasks/main.yml
```
Your directory structure should now look like:
```
my-apb/
├── apb.yml
├── Dockerfile
├── playbooks
│   └── provision.yml
└── roles
    └── provision-my-apb
        └── tasks
            └── main.yml
```

Rebuilding the APB (`apb build ...`) and running the provision command (`docker run ...`) should output the output from the Ansible playbook with no changes:
```
PLAY RECAP *********************************************************************
localhost                  : ok=0    changed=0    unreachable=0    failed=0
```

##### Provision - Creating a namespace
Our first task we'll add to the role is creating a project namespace for our created resources.  In `provision-my-apb/tasks/main.yml` paste the following:
```yaml
- name: create namespace if it doesn't exist
  openshift_v1_project:
    name: '{{ namespace }}'
```
As you can see, we're using the `namespace` variable passed in from `--extra-vars`, earlier.  Without it, our role would result in an error.  Rebuilding the APB using `apb build <docker-org>/my-apb` and running the provision command will look like the following:
```
$ apb build <docker-org>/my-apb
$ docker run -e "OPENSHIFT_TARGET=https://<oc-cluster-host>:<oc-cluster-port>" -e "OPENSHIFT_USER=admin"  -e "OPENSHIFT_PASS=admin" <docker-org>/my-apb provision --extra-vars 'namespace=my-apb'

Login successful.

You have access to the following projects and can switch between them with 'oc project <projectname>':

    ansible-service-broker
  * default
    my-apb
    kube-system
    myproject
    openshift
    openshift-infra
    service-catalog

Using project "default".
Welcome! See 'oc help' to get started.

PLAY [my-apb provision] ***********************************************

TASK [ansible.kubernetes-modules : Install latest openshift client] *************
skipping: [localhost]

TASK [provision-my-apb : create namespace if it doesn't exist] ********
ok: [localhost]

PLAY RECAP *********************************************************************
localhost                  : ok=1    changed=0    unreachable=0    failed=0
```
You can verify the project was created by running `oc get projects` to get a list or by viewing the projects in the console UI.  Now we have a project named **_my-apb_** for all the resources we'll create in the following sections.

##### Provision - Creating a deployment config
At the minimum, our APB should deploy the application [pods](https://docs.openshift.org/latest/architecture/core_concepts/pods_and_services.html#pods).  We'll do this by specifying a [deployment config](https://docs.openshift.org/latest/architecture/core_concepts/deployments.html#deployments-and-deployment-configurations).  Add the following to `provision-my-apb/tasks/main.yml` underneath the namespace task.
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
      - container_port: 80
        protocol: TCP
```
The `namespace` field will tell the object where to be created.
The `labels` are used to help us organize and categorize objects.
The `replicas: 1` field specifies that we only want 1 pod.
The `selector` section is a label query over pods.
In the `containers` section, we have specified the containerized hello-world app from the ansibleplaybookbundle organization to use and exposed it by TCP on port 80.  For more information, you can visit the ansible-kubernetes-modules [code](https://github.com/ansible/ansible-kubernetes-modules/blob/master/library/openshift_v1_deployment_config.py) documentation for a full accounting of all fields.  If you build the apb and run the provision command, you will see the the new task in the output.
```
TASK [provision-my-apb : create deployment config] ********************
changed: [localhost]
```
At this point we can set our current project to hello-world and query for the deployment config and pods to see the running pods
```
oc project my-apb
oc get dc
oc describe dc/hello-world
oc get pods
```
You will also be able to see the deployed application in the console UI at https://<oc-cluster-host>:<oc-cluster-port>/console/project/hello-world/overview.  The only way to use this pod currently is to use `oc describe pods/<pod-name>`, to find out it's IP address and access it directly.  If we had multiple pods, they'd be accessed separately.  To treat them like a single host, we'd need to create a **_service_**

##### Provision - Creating a service
We want to use multiple [pods](https://docs.openshift.org/latest/architecture/core_concepts/pods_and_services.html#pods), load balance them, and create a [service](https://docs.openshift.org/latest/architecture/core_concepts/pods_and_services.html#services) so that a user can access them as a single host.  Let's create that service and modify the same `provision-my-apb/tasks/main.yml` by adding the following:
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
        port: 80
        target_port: 80
```
The `selector` will allow the *hello-world* service to include the correct pods.  The `ports` will take the target port from the pods and expose them as a single port for the service.  We can target the port specified using it's `name`.  More information is available in the [k8s_v1_service module](https://github.com/ansible/ansible-kubernetes-modules/blob/master/library/k8s_v1_service.py).  If you build the apb and run the provision command, you will see the the new task in the output.
```
TASK [provision-my-apb : create hello-world service] ******************
changed: [localhost]
```
You can click on the new service under **_Networking_** in the application on the overview page or under **_Applications -> Services_**.  The service's IP address will be shown which you can use to access the load balanced application.  To view the service information from the command line, you can do the following:
```
oc project my-apb
oc get services
oc describe services/hello-world
```
The describe command will show the IP address to access the service. Using an IP address for users to access our application isn't generally what we want.  Generally, we want to create a [route](https://docs.openshift.org/latest/architecture/core_concepts/routes.html).

##### Provision - Creating a route
We want to allow access to our application through a reliable named [route](https://docs.openshift.org/latest/architecture/core_concepts/routes.html).
```yaml
- name: create hello-world route
  openshift_v1_route:
    name: hello-world
    namespace: '{{ namespace }}'
    labels:
      app: hello-world
      service: hello-world
    to_name: hello-world
    spec_port_target_port: web
```
The `to_name` is name of the target service.  `spec_port_target_port` refers to the name of the target service's port.  More information is available in the [openshift_v1_route module](https://github.com/ansible/ansible-kubernetes-modules/blob/master/library/openshift_v1_route.py).
If you build the apb and run the provision command, you will see the the new task in the output.
```
TASK [provision-my-apb : create hello-world route] ******************
changed: [localhost]
```
On the console UI overview page for the hello-world project, you will now see an active and clickable route link listed on the application.  Clicking on the route or visiting the URL will bring up the hello-world app.  From the command line, you can also view the route information.
```
oc project my-apb
oc get routes
oc describe routes/hello-world
```

At this point, our hello-world application is fully functional, load balanced, scalable, and accessible.
#### Bind

#### Unbind

#### Deprovision
In the deprovision task, we need to destroy all provisioned resources, usually in reverse order.  The exception is the namespace we created, since users may have added other resources in the project and we may not want to delete resources created by other means.

To add the deprovision action, we'll add a yaml file `deprovision.yml` inside the `playbooks` directory.
```
my-apb/
├── apb.yml
├── Dockerfile
├── playbooks
│   ├── deprovision.yml
│   └── provision.yml
└── roles
    └── provision-my-apb
        └── tasks
            └── main.yml

```

Now let's paste in the following code into `playbooks/deprovision.yml`:
```yaml
- name: my-apb deprovision
  hosts: localhost
  gather_facts: false
  connection: local
  roles:
  - role: ansible.kubernetes-modules
    install_python_requirements: no
  - role: deprovision-my-apb
    playbook_debug: false
```
The content looks the same as the provision task, except it's calling a different role which does the actual work.  Let's create that role now. Create a new file called `main.yml` inside a `roles/deprovision-my-apb` directory.
```
mkdir -p roles/deprovision-my-apb/tasks
touch roles/deprovision-my-apb/tasks/main.yml
```
Your directory structure should now look like:
```
my-apb/
├── apb.yml
├── Dockerfile
├── playbooks
│   ├── deprovision.yml
│   └── provision.yml
└── roles
    ├── deprovision-my-apb
    │   └── tasks
    │       └── main.yml
    └── provision-my-apb
        └── tasks
            └── main.yml
```
Let's paste in the following code in `roles/deprovision-my-apb/tasks/main.yml` and then we'll take a look at it.
```yaml
- openshift_v1_route:
    name: hello-world
    namespace: '{{ namespace }}'
    state: absent

- k8s_v1_service:
    name: hello-world
    namespace: '{{ namespace }}'
    state: absent

- openshift_v1_deployment_config:
    name: hello-world
    namespace: '{{ namespace }}'
    state: absent
```
In `provision.yml`, created earlier, we created the deployment config, service, then route. For the **_deprovision_** action, we'll want to delete the resources in reverse order.  We do so by identifying the resource by `namespace` and `name` and then marking it as `state: absent`.  That's all there is to it.

[TODO]: # (Currently, the replication controller is being left behind even though it's a dependent resource.  This may be a bug and we need to look into it or else we'll have to add a way to gracefully handle its deletion)

### More information
* [Design](design.md) - overall design of Ansible Playbook Bundles
* [Developers](developers.md) - in depth explanation of Ansible Playbook Bundles
* [OpenShift Origin Docs](https://docs.openshift.org/latest/welcome/index.html)
* The [ansible-kubernetes-modules](https://github.com/ansible/ansible-kubernetes-modules) project.
* [Example APBs](https://github.com/fusor/apb-examples)
* [Ansible Service Broker](https://github.com/fusor/ansible-service-broker)
