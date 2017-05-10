# Ansible Playbook Bundle (APB)

An **Ansible Playbook Bundle (APB)** is a lightweight application definition (meta-container). They are used to define and deploy complex groups of applications, deployment configs, deployments, and services to an [OpenShift Origin](https://github.com/OpenShift/origin) cluster running the [Ansible Service Broker](https://github.com/fusor/ansible-service-broker).  APBs offer more power and simple configuration by leveraging the power of [Ansible](https://www.ansible.com/). APBs have the following features:

* Metadata contains list of required/optional parameters for use during deployment.
* Leverages existing investment in Ansible Roles / Playbooks.
* Actions under a directory with named  **_playbooks_** and metadata defined in **_apb.yml_**.
* Developer Tooling to drive a guided approach.
* Easily modified or extended.

## Installing the ***apb*** tool
##### Prerequisites
[Docker](https://www.docker.com/) must be correctly [installed](https://docs.docker.com/engine/installation/) and running on the system.

##### RPM Installation
Download from [here](????)
Install using dnf/yum
```
sudo yum install ansible-playbook-bundle
```

##### Installing from source
Clone this repo
```
git clone https://github.com/fusor/ansible-playbook-bundle.git
```
Install requirements and run the setup script (requires python)
```
sudo pip install -r src/requirements.txt && sudo python setup.py install
```
Alternatively you can use [tito](http://github.com/dgoodwin/tito) to install.
```bash
tito build --test --rpm -i
```

##### Test apb tooling
Run `apb help` to make sure the tool is installed correctly
```
$ apb help
usage: apb [-h] [--debug] [--project BASE_PATH] {init,help,prepare,build} ...

APB tooling forassisting in building and packaging APBs.

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

## Documentation
* [Getting Started](docs/getting_started.md) - step by step tutorial to create an Ansible Playbook Bundle
* [Design](docs/design.md) - overall design of Ansible Playbook Bundles
* [Developers](docs/developers.md) - in depth explanation of Ansible Playbook Bundles
* [ISV](docs/isv.md) - integrating with existing Ansible roles

<a name="links"></a>
## Links
* Ansible Service Broker [https://github.com/fusor/ansible-service-broker ](https://github.com/fusor/ansible-service-broker)
* YouTube channel: [APB](https://www.youtube.com/channel/UCE0uKh7SmjsOL3Zv0jnhgaA)
