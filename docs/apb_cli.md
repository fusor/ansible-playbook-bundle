# APB CLI Tool

`apb` is a tool for helping APB authors create, build, and publish
their APBs to container registries. It enforces best practices and takes
care of the details so they should be easy to deploy.

1. [Installation](#installing-the-apb-tool)
    * [Prerequisites](#prerequisites)
    * [Running from a container](#running-from-a-container)
    * [RPM Installation](#rpm-installation)
    * [Installing from source](#installing-from-source)
        * [Python/VirtualEnv](#installing-from-source---pythonvirtualenv)
        * [Installing from source - Tito](#installing-from-source---tito)
    * [Test APB tooling](#test-apb-tooling)
1. [Typical Workflows](#typical-workflows)
    * [Local Registry](#local-registry)
    * [Remote Registry](#remote-registry)
1. [APB Commands](#apb-commands)
    * [Creating APBs](#creating-apbs)
        * [init](#init)
        * [prepare](#prepare)
        * [build](#build)
        * [push](#push)
        * [test](#test)
    * [Broker Utilities](#broker-utilities)
        * [list](#list)
        * [bootstrap](#bootstrap)
        * [remove](#remove)
        * [relist](#relist)    
    * [Other](#other)
        * [help](#help)    


## Installing the **_apb_** tool

#### Prerequisites

[Docker](https://www.docker.com/) must be correctly installed and running on the system.

#### Running from a container

Pull the container:
```bash
docker pull docker.io/ansibleplaybookbundle/apb-tools
```

Create an alias in your `.bashrc` or somewhere else sane for your shell:
```bash
alias apb='docker run --rm --privileged -v $PWD:/mnt -v $HOME/.kube:/.kube -v /var/run/docker.sock:/var/run/docker.sock -u $UID docker.io/ansibleplaybookbundle/apb-tools'
```

You should be able to start working by running `apb init my_apb`. The first run may take awhile if you did not pull the image.

If you would prefer to use atomic rather than an alias this is also possible:
```bash
atomic run docker.io/ansibleplaybookbundle/apb-tools init my_apb
```

There are three tags to choose from:
- **latest**: more stable, less frequent releases
- **nightly**: following upstream commits, installed from RPM
- **canary**: following upstream commits, installed from source build

#### RPM Installation

For RHEL or CentOS 7:
```
su -c 'wget https://copr.fedorainfracloud.org/coprs/g/ansible-service-broker/ansible-service-broker-latest/repo/epel-7/group_ansible-service-broker-ansible-service-broker-latest-epel-7.repo -O /etc/yum.repos.d/ansible-service-broker.repo'

sudo yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
sudo yum -y install apb
```


For Fedora 26 or Fedora 27:
```
sudo dnf -y install dnf-plugins-core
sudo dnf -y copr enable @ansible-service-broker/ansible-service-broker-latest
sudo dnf -y install apb
```

#### Installing from source

<a id="python-virtualenv"></a>
##### Installing from source - Python/VirtualEnv

Clone this repo
```
git clone https://github.com/fusor/ansible-playbook-bundle.git
```
Install python-virtualenv, create a virtualenv, and activate it.
```
sudo dnf install -y python-virtualenv
virtualenv /tmp/apb
source /tmp/apb/bin/activate
```
Install requirements and run the setup script (requires python)
```
cd ansible-playbook-bundle && pip install -U setuptools && pip install -r src/requirements.txt && python setup.py install
```

Optionally, if actively developing on the project, install the
testing requirements:
```
pip install -r src/test-requirements.txt
```

Reactivate the `apb` virtualenv in other shell sessions using `source /tmp/apb/bin/activate` if needed.

##### Installing from source - Tito

Alternatively you can use [tito](http://github.com/dgoodwin/tito) to install.
```bash
tito build --test --rpm -i
```

#### Test APB Tooling
Run `apb help` to make sure the tool is installed correctly
```
$ apb help
usage: apb [-h] [--debug] [--project BASE_PATH]
           {init,help,prepare,push,bootstrap,list,remove,build} ...

APB tooling for assisting in building and packaging APBs.

optional arguments:
  -h, --help            show this help message and exit
  --debug               Enable debug output
  --project BASE_PATH, -p BASE_PATH
                        Specify a path to your project. Defaults to CWD.

subcommand:
  {init,help,prepare,push,bootstrap,list,remove,build}
    init                Initialize the directory for APB development
    help                Display this help message
    prepare             Prepare an ansible-container project for APB packaging
    push                Push local APB spec to an Ansible Service Broker
    bootstrap           Tell Ansible Service Broker to reload APBs from the
                        container repository
    list                List APBs from the target Ansible Service Broker
    remove              Remove APBs from the target Ansible Service Broker
    build               Build and package APB container

```

#### Access Permissions

The `apb` tool requires you to be logged in as a tokened cluster user (`system:admin`
is not sufficient because it does not have a token that can be used for the tool's authentication).
In addition, there are a number of `RoleBinding`s and `ClusterRoleBindings` that must
exist to permit the full breadth of the `apb` tool's functions.

The easiest option is to ensure the user has the `cluster-admin` `ClusterRoleBinding`.
**To be clear, this is effectively cluster root and should only be used in a development setting**.

```
oc adm policy add-cluster-role-to-user cluster-admin <user>
oc login -u <user>
```

If you would like a more strictly permissioned environment, we have an [Openshift Template](templates/openshift-permissions.template.yaml)
available that can be applied with the following command:

`oc process -f templates/openshift-permissions.template.yaml -p USER=<your_desired_user> | oc create -f -`.

By default, the template will permission the `developer` user. If that is your user, it
is safe to leave off the `-p` flag, which overrides the default value. Obviously, this
command must be run by a user with sufficient permissions to create the various roles.
The `developer` account does not have such permissions. `oc login -u system:admin` should
be sufficient.

## Typical Workflows

#### Local Registry
In order to use the internal OpenShift Docker Registry to source APBs, you must have configured the Ansible Service Broker to use the `local_openshift` type registry adapter. Please see the [config](https://github.com/openshift/ansible-service-broker/blob/master/docs/config.md#local-openshift-registry) section for more information.

NOTE: If you are working with a minishift cluster and the [ansible-service-broker addon](https://github.com/minishift/minishift-addons/tree/master/add-ons/ansible-service-broker),
you must first configure your shell to use the minishift Docker daemon. This can
be done with `eval $(minishift docker-env)`. For more info, see [minishift's documentation for working with its docker registry](https://docs.openshift.org/latest/minishift/using/docker-daemon.html).


```bash
apb init my-new-apb
cd my-new-apb
apb build
apb push
apb list
```

If you are using a namespace other than the default `openshift` namespace to host your APBs then you can use the following command:
```
apb push --namespace <namespace>
```

#### Remote Registry
Ansible Service Broker can also be [configured](https://github.com/openshift/ansible-service-broker/blob/master/docs/config.md#dockerhub-registry) to use a remote registry and org such as [docker.io/ansibleplaybookbundle](https://hub.docker.com/u/ansibleplaybookbundle/) or your own personal account.  In order to use this for developing APBs, you can build and push to your remote registry and then `bootstrap` to reload your APBs.

```bash
apb init my-new-apb
cd my-new-apb
apb build --tag docker.io/my-org/my-new-apb
docker push docker.io/my-org/my-new-apb
apb bootstrap
apb list
```

## APB Commands
[Creating APBs](#creating-apbs)
* [init](#init)
* [prepare](#prepare)
* [build](#build)
* [push](#push)
* [test](#test)
    
[Broker Utilities](#broker-utilities)
* [list](#list)
* [bootstrap](#bootstrap)
* [remove](#remove)
* [relist](#relist)    

[Other](#other)
* [help](#help)    

<a id="creating-apbs"></a>

---

### `init`

##### Description
Initializes a directory structure for a new apb.  Also creates example files for the new APB with sensible defaults.

##### Usage
```bash
apb init [OPTIONS] NAME
```
##### Arguments
_NAME_: Name of the APB and directory to be created

##### Options

| Option, shorthand      | Description |
| :---                   | :---        |
| --help, -h             | Show help message |
| --force                | Force re-init and overwrite the directory  |
| --async {required,optional,unsupported} | Specify asynchronous operation on application. Usually defaulted to "optional"|
| --bindable             | Generate an application with bindable settings |
| --skip-provision       | Do not generate provision playbook and role |
| --skip-deprovision     | Do not generate deprovision playbook and role |
| --skip-bind            | Do not generate bind playbook and role |
| --skip-unbind          | Do not generate unbind playbook and role |
| --skip-roles           | Do not generate any roles |



##### Examples
Create directory my-new-apb
```bash
apb init my-new-apb
# my-new-apb/
# ├── apb.yml
# ├── Dockerfile
# ├── playbooks
# │   ├── deprovision.yml
# │   └── provision.yml
# └── roles
#     ├── deprovision-my-new-apb
#     │   └── tasks
#     │       └── main.yml
#     └── provision-my-new-apb
#         └── tasks
#             └── main.yml
```

Create directory my-new-apb but skip generating deprovision playbook and roles.
```bash
apb init my-new-apb --skip-deprovision
# my-new-apb/
# ├── apb.yml
# ├── Dockerfile
# ├── playbooks
# │   └── provision.yml
# └── roles
#     └── provision-my-new-apb
#         └── tasks
#             └── main.yml
```

Create directory my-new-apb, overwriting any old versions. The apb will be configured to be bindable and require async.
```bash
apb init my-new-apb --force --bindable --async required
# my-new-apb/
# ├── apb.yml
# ├── Dockerfile
# ├── playbooks
# │   ├── bind.yml
# │   ├── deprovision.yml
# │   ├── provision.yml
# │   └── unbind.yml
# └── roles
#     ├── bind-my-new-apb
#     │   └── tasks
#     │       └── main.yml
#     ├── deprovision-my-new-apb
#     │   └── tasks
#     │       └── main.yml
#     ├── provision-my-new-apb
#     │   └── tasks
#     │       └── main.yml
#     └── unbind-my-new-apb
#         └── tasks
#             └── main.yml
```

---
### `prepare`

##### Description
Compiles the apb into base64 encoding and writes it as a label to the Dockerfile.  

This will allow the Ansible Service Broker to read the apb metadata from the registry without downloading the images.  This command must be run from inside the APB directory.  Running the `build` command will automatically run prepare as well, meaning you generally don't need to run `prepare` by itself.

##### Usage
```bash
apb prepare [OPTIONS]
```

##### Options
| Option, shorthand  | Description |
| :---               | :---        |
| --help, -h         | Show help message |
| --dockerfile DOCKERFILE, -f DOCKERFILE  | Writes the apb spec to the target filename instead of a file named "Dockerfile"  |


##### Examples
Writes the label for the spec field in `Dockerfile`
```bash
apb prepare
```

Writes the label for the spec field in `Dockerfile-custom`
```bash
apb prepare --dockerfile Dockerfile-custom
```

---
### `build`

##### Description
Builds the image for the APB. 

Similar to running `apb prepare` and `docker build` with a tag. 

##### Usage
```bash
apb build [OPTIONS]
```

##### Options

| Option, shorthand  | Description |
| :---               | :---        |
| --help, -h         | Show help message |
| --tag TAG          | Sets the tag of the built image to a string in the format registry/org/name|
| --dockerfile DOCKERFILE, -f DOCKERFILE  | Writes the apb spec to the target filename instead of a file named "Dockerfile"  |


##### Examples
Build the image and use the name field from apb.yml as the tag.
```bash
apb build
```

Build the image and use the tag docker.io/my-org/my-new-apb.
```bash
apb build --tag docker.io/my-org/my-new-apb
```

Build the image using the file "Dockerfile-custom" as the Dockerfile definition.
```bash
apb build --dockerfile Dockerfile-custom
```

---
### `push`

##### Description
Uploads the APB to a local openshift registry or a broker mock registry where it will be read by the Ansible Service Broker. 

When using the broker's mock registry, the spec is uploaded and will be displayed in OpenShift, but OpenShift will pull the image from the registry normally.  Usually that means the docker registry where `oc cluster up` was performed.

When using the local openshift registry, the image is uploaded to OpenShift directly.

##### Usage
```bash
apb push [OPTIONS]
```

##### Options

| Option, shorthand  | Description |
| :---               | :---        |
| --help, -h         | Show help message |
| --broker BROKER_URL | Route to the Ansible Service Broker |
| --namespace NAMESPACE | Namespace to push to internal OpenShift registry |
| --registry-service-name REG_SVC_NAME | Name of service for the internal OpenShift registry |
| --registry-route REG_ROUTE | Name of service for the internal OpenShift registry |
| --registry-namespace REG_NAMESPACE | Name of service for the internal OpenShift registry |
| --dockerfile DOCKERFILE, -f DOCKERFILE | Dockerfile to build internal registry image.  Usually defaults to "Dockerfile" but can be set to any filename |
| --secure           | Use secure connection to Ansible Service Broker |
| --username  USERNAME| Basic auth username to be used in broker communication  |
| --password  PASSWORD| Basic auth password to be used in broker communication  |
| --no-relist        | Do not relist the catalog after pushing an apb to the broker  |
| --broker-name      | Name of the ServiceBroker k8s resource  |
| --push-to-broker   | Use the OpenShift Ansible Broker mock registry endpoint |


##### Examples
Push to the local OpenShift registry
```bash
apb push
```
Push to the Ansible Service Broker development endpoint
```bash
apb push --push-to-broker
```
Push to the local OpenShift registry under namespace `leto`
```bash
apb push --namespace leto
```

---
### `test`

##### Description
Runs the APB unit tests.

##### Usage
```bash
apb test [OPTIONS]
```

##### Options

| Option, shorthand  | Description |
| :---               | :---        |
| --help, -h         | Show help message |
| --tag TAG          | Sets the tag of the built image to a string in the format registry/org/name |


##### Examples
Run the tests
```bash
apb test
```

Run the tests but use a specific tag on the built image
```bash
apb test --tag docker.io/my-org/my-new-apb
```

<a id="broker-utilities"></a>

---

### `list`

##### Description
Lists all the APBs the broker has loaded

##### Usage
```bash
apb list [OPTIONS]
```

##### Options

| Option, shorthand   | Description |
| :---                | :---        |
| --help, -h          | Show help message |
| --broker BROKER_URL | Route to the Ansible Service Broker|
| --secure            |  Use secure connection to Ansible Service Broker |
| --verbose, -v       |  Output verbose spec information from Ansible Service Broker |
| --output {yaml,json}, -o {yaml,json}| Specify verbose output format in yaml (default) or json |
| --username BASIC_AUTH_USERNAME, -u BASIC_AUTH_USERNAME | Specify the basic auth username to be used |
| --password BASIC_AUTH_PASSWORD, -p BASIC_AUTH_PASSWORD | Specify the basic auth password to be used |


##### Examples

Basic list of APBs including name, ID, and description
```bash
apb list
```

List verbose pretty printed specs
```bash
apb list -v 
```

List all the json output
```bash
apb list -v -o json
```

---
### `bootstrap`

##### Description
Requests the Ansible Service Broker to reload all APBs from the registries.

##### Usage
```bash
apb bootstrap [OPTIONS]
```

##### Options

| Option, shorthand   | Description |
| :---                | :---        |
| --help, -h          | Show help message |
| --broker BROKER_URL | Route to the Ansible Service Broker |
| --secure            | Use secure connection to Ansible Service Broker |
| --no-relist         | Do not relist the catalog after bootstrapping the broker |
| --username BASIC_AUTH_USERNAME, -u BASIC_AUTH_USERNAME | Specify the basic auth username to be used |
| --password BASIC_AUTH_PASSWORD, -p BASIC_AUTH_PASSWORD | Specify the basic auth password to be used |
| --broker-name BROKER_NAME | Name of the ServiceBroker k8s resource |


##### Examples
Basic reload of APBs
```bash
apb bootstrap
```


---
### `remove`

##### Description
Removes one (or all) APBs from the broker.

##### Usage
```bash
apb remove [OPTIONS]
```

##### Options

| Option, shorthand   | Description |
| :---                | :---        |
| --help, -h          | Show help message |
| --broker BROKER_URL | Route to the Ansible Service Broker|
| --secure            | Use secure connection to Ansible Service Broker |
| --all               | Remove all stored APBs |
| --id ID             | ID of APB to remove |
| --secure            | Use secure connection to Ansible Service Broker |
| --username BASIC_AUTH_USERNAME, -u BASIC_AUTH_USERNAME | Specify the basic auth username to be used |
| --password BASIC_AUTH_PASSWORD, -p BASIC_AUTH_PASSWORD | Specify the basic auth password to be used |
| --no-relist         | Do not relist the catalog after deletion|


##### Examples                                                                                                                                         
Remove an APB using an ID
```bash
apb remove --id ca91b61da8476984f18fc13883ae2fdb
oc delete clusterserviceclass ca91b61da8476984f18fc13883ae2fdb
```
Deleting the `clusterserviceclass` removes the associated APB from the Service Catalog.

*Note: If you need an ID of an APB, use* `apb list`.
```bash
$ apb list
ID                                NAME                     DESCRIPTION
ca91b61da8476984f18fc13883ae2fdb  dh-etherpad-apb          Note taking web application
```  

Remove all APBs
```bash
apb remove --all
```

---
### `relist`

##### Description
Forces service catalog to relist the provided services to match the broker.

##### Usage
```bash
apb relist [OPTIONS]
```

##### Options
| Option, shorthand   | Description |
| :---                | :---        |
| --help, -h          | Show help message |
| --broker-name BROKER_NAME | Name of the ServiceBroker k8s resource |
| --secure            | Use secure connection to Ansible Service Broker
| --username BASIC_AUTH_USERNAME, -u BASIC_AUTH_USERNAME | Specify the basic auth username to be used |
| --password BASIC_AUTH_PASSWORD, -p BASIC_AUTH_PASSWORD | Specify the basic auth password to be used |


##### Examples
```bash
apb relist
```

<a id="other"></a>

---

### `help`

##### Description
Displays a help message

##### Usage
```bash
apb help
```

##### Examples
```bash
apb help
```

```bash
apb -h
```
