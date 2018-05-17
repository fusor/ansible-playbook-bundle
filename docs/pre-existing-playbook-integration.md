# Integrating Pre-existing Playbooks with APBs

1. [Introduction](#introduction-to-playbook-integration)
1. [Distinguishing Actions](#distinguishing-actions)
    1. [Ansible 'when' Statement](#ansible-when-statement)
1. [Pre-existing Playbook Installation](#pre-existing-playbook-installation)
    1. [Ansible Galaxy](#ansible-galaxy)
    1. [RPMs](#rpms)
    1. [GitHub Source](#github-source)
1. [Running the Pre-existing Playbooks](#running-the-pre-existing-playbooks)
    1. [Shim Playbook](#shim-playbook)

## Introduction to Playbook Separation
APBs expect playbooks to be named after an APB action like
`playbooks/provision.yml` locally inside the container.  This can prove
problematic when trying to use a pre-existing playbook or a well tested
production playbook that you don't want to change to create an APB.  But, since
Ansible allows playbooks to import other playbooks, roles, and tasks, we can
create `playbooks/provision.yml` locally and use it to point to pre-existing
playbooks without having to change those playbooks to fit the APB directory
structure.  This allows for the developer to keep production playbook code where
it is and import that code into the APB's container from Ansible Galaxy, rpms,
or git repos.

There are three things required for integration:
  1. Ansible playbooks that distinguish between APB actions
  2. Installing the pre-existing playbooks in the APB container
  3. The APB uses a playbook to call the pre-existing playbooks

## Distinguishing Actions
Since there are multiple action an APB can use, pre-existing
playbooks will need to distinguish which action to perform.  The APB will
provide to the playbooks with the variable `apb_action` for this purpose.

#### Ansible 'when' Statement
Ansible has the `when:` to only run tasks if a condition is met. Add these
to individual tasks, roles, or playbooks to distinguish actions.

```yaml
---
- name: Provision mysql
  shell: oc create -f mysql-rc.yaml
  when: "{{ apb_action }}" == "provision"
```

At the playbook level:

```yaml
- hosts: all
  tasks:
    - import_role:
        name: provision mysql
        tasks_from: "{{ apb_action }}"
```

## Pre-existing Playbook Installation
The playbooks need to be on the container file system so it can be
referenced. Here are a few ways to install a pre-existing playbook inside
the Dockerfile:

#### Ansible Galaxy
Using [kubevirt-apb](https://github.com/ansibleplaybookbundle/kubevirt-apb) as an example, we'll install the [kubevirt-ansible](https://github.com/kubevirt/kubevirt-ansible/) playbooks using ansible-galaxy.

From the [Dockerfile](https://github.com/ansibleplaybookbundle/kubevirt-apb/blob/master/Dockerfile):
```bash
...

COPY requirements.yml /opt/ansible/requirements.yml
COPY inventory /etc/ansible/hosts

RUN ansible-galaxy install -r /opt/ansible/requirements.yml
RUN chmod -R g=u /opt/{ansible,apb} /etc/ansible/roles

USER apb
```

#### RPMs
If you distribute your production playbook as an RPM, install the RPM in the APB
container.

```bash
...

RUN yum install -y production-mysql-playbooks
...
```

#### GitHub Source
Finally, you can install the playbooks right from source by cloning from git or
curling a tarball.

```bash
...

RUN git clone https://github.com/beekhof/galera-ansible
...
```

## Running the Pre-existing Playbooks
Now that the pre-existing playbooks are local to the APB, create playbooks
for the actions and import playbooks, roles, and tasks from the pre-existing
playbooks.

#### Shim playbook
Create playbooks ```provision.yml``` and ```deprovision.yml```, then start
making calls to the pre-existing playbooks.

playbooks/provision.yml
```yaml
- name: Provision Production mysql
  hosts: localhost
  gather_facts: false
  connection: local
  roles:
  - role: ansible.kubernetes-modules
    install_python_requirements: no
  - role: ansibleplaybookbundle.asb-modules
  - role: mysql-production
  vars:
    apb_action: "provision"

```

Here's an example of importing an entire playbook:

playbooks/provision.yml
```yaml
- name: Provision KubeVirt
  hosts: localhost
  gather_facts: false
  connection: local
  roles:
  - role: ansible.kubernetes-modules
    install_python_requirements: no
  - role: ansibleplaybookbundle.asb-modules

- import_playbook: "/etc/ansible/roles/kubevirt-ansible/playbooks/kubevirt.yml"
  vars:
    apb_action: "provision"
```
