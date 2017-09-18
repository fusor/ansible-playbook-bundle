# Ansible Playbook Bundle (APB)

An **Ansible Playbook Bundle (APB)** is a lightweight application definition (meta-container). They are used to define and deploy complex groups of applications, deployment configs, deployments, and services to an [OpenShift Origin](https://github.com/OpenShift/origin) cluster running the [Ansible Service Broker](https://github.com/openshift/ansible-service-broker).  APBs offer more power and simple configuration by leveraging the power of [Ansible](https://www.ansible.com/). APBs have the following features:

* Metadata contains list of required/optional parameters for use during deployment.
* Leverages existing investment in Ansible Roles / Playbooks.
* Actions under a directory with named  **_playbooks_** and metadata defined in **_apb.yml_**.
* Developer tooling to drive a guided approach.
* Easily modified or extended.

## Installing the ***apb*** tool
##### Prerequisites
[Docker](https://www.docker.com/) must be correctly [installed](https://docs.docker.com/engine/installation/) and running on the system.

##### Running from a container

Create an alias in your .bashrc or somewhere else sane for your shell:  
`alias apb='docker run --rm --privileged -v $PWD:/mnt -v $HOME/.kube:/.kube -v /var/run/docker.sock:/var/run/docker.sock -u $UID docker.io/ansibleplaybookbundle/apb'`

You should be able to start working by running 'apb init *org/repo*. The first run in particular may take awhile to return while the image is pulled.

If you would prefer to use atomic rather than an alias this is also possible:  
`atomic run docker.io/ansibleplaybookbundle/apb init foo/bar`

There are three tags to choose from:  
**latest**: more stable, less frequent releases  
**nightly**: following upstream commits, installed from RPM  
**canary**: following upstream commits, installed from source build  

##### RPM Installation

For RHEL or CentOS 7:
```
su -c 'wget https://copr.fedorainfracloud.org/coprs/g/ansible-service-broker/ansible-service-broker/repo/epel-7/group_ansible-service-broker-ansible-service-broker-epel-7.repo -O /etc/yum.repos.d/ansible-service-broker.repo'

sudo yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
sudo yum -y install apb
```


For Fedora 25 or Fedora 26:
```
sudo dnf -y install dnf-plugins-core
sudo dnf -y copr enable @ansible-service-broker/ansible-service-broker
sudo dnf -y install apb
```

##### Installing from source

###### Installing from source - Python/VirtualEnv

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

###### Installing from source - Tito

Alternatively you can use [tito](http://github.com/dgoodwin/tito) to install.
```bash
tito build --test --rpm -i
```

##### Test APB tooling
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

## Documentation
* [Getting Started](docs/getting_started.md) - step by step tutorial to create an Ansible Playbook Bundle
* [Design](docs/design.md) - overall design of Ansible Playbook Bundles
* [Developers](docs/developers.md) - in depth explanation of Ansible Playbook Bundles

<a name="links"></a>
## Links
* Ansible Service Broker [https://github.com/openshift/ansible-service-broker ](https://github.com/openshift/ansible-service-broker)
* YouTube channel: [Ansible Service Broker](https://www.youtube.com/channel/UC04eOMIMiV06_RSZPb4OOBw)
* YouTube channel: [APB](https://www.youtube.com/channel/UCE0uKh7SmjsOL3Zv0jnhgaA)

## Initialize skeleton APB application example
```
apb init my_apb --async=optional --bindable --org my_organization
```

This gives us the following example apb.yaml 
```
name: my-apb
image: my-org/my-apb
description: "my-apb description"
bindable: True
async: optional
metadata: {}
plans:
  - name: my-plan
    description: "my-plan description"
    free: True
    metadata: {}
    parameters: []
