# Developer Guide

## APB Examples
For completed APB examples, visit [APB Examples Repo](https://github.com/fusor/apb-examples) .

## Creating Ansible Playbook Bundles (APBs)

In order to create an APB, you will need to start with a skeleton APB directory structure.  The layout of the [directory structure](design.md#directory-structure) is shown in the [design](design.md) document.

### APB Init
You may create the directory structure yourself, or you can use the `apb init` command to create a simple skeleton structure, and modify it to your needs.  You will need to specify the name of your APB as a minimum input.  Visit the [APB Tooling README](https://github.com/fusor/ansible-playbook-bundle/blob/master/src/README.md) for more information.

Run the `apb init` command
```bash
$ apb init my-apb
```

### Initial Directory Structure
The following APB directory structure will be created:
```bash
my-apb/
├── apb.yml
├── Dockerfile
├── playbooks/
└── roles/
```
### Spec File
The `apb init` will auto generate a spec file.  You must edit this spec file to fit your application. The following is the spec file for [etherpad-apb](https://github.com/fusor/apb-examples/blob/master/etherpad-apb/apb.yml).  More examples can be found in the [apb-examples repo](https://github.com/fusor/apb-examples)

```yml
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

#### Parameters

APB's with no parameters would define the `parameters` field as follows:
```yml
parameters: []
```

New `parameters` can be added to the spec file as shown below:
```yaml
parameters:
  - mariadb_name:                   # name of the parameter
    title: MariaDB Database Name    # title/description (shown in the UI)
    type: string                    # type of the parameter (e.g. string, int, enum)
    default: etherpad               # default value 
```

If a parameter is required, list the parameter name in the `required` section as shown below:
```yaml
required:
 - mariadb_name
```

### Adding optional variables to an Ansible playbook bundle via environment variables

To pass variables into an APB, you will need to escape the variable substitution in your `.yml` files. For example, the below is a section of the [main.yml](https://github.com/fusor/apb-examples/blob/master/etherpad-apb/roles/provision-etherpad-apb/tasks/main.yml#L89) in the [etherpad-apb](https://github.com/fusor/apb-examples/tree/master/etherpad-apb):

```yml
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

The above expects the `namespace` variable to be defined, which was not part of the `parameters` in the spec file `apb.yml`.

To define variables, use the `main.yml` file under the `defaults` folder to define/set other variables for your APB.  For example, below is the [defaults/main.yml](https://github.com/fusor/apb-examples/blob/master/etherpad-apb/roles/provision-etherpad-apb/defaults/main.yml) for the `etherpad-apb`:

```yml
---
playbook_debug: no
namespace: "{{ lookup('env','NAMESPACE') | default('etherpad-apb', true) }}"
mariadb_root_password: "{{ lookup('env','MYSQL_ROOT_PASSWORD') | default('admin', true) }}"
mariadb_name: "{{ lookup('env','MYSQL_DATABASE') | default('etherpad', true) }}"
mariadb_user: "{{ lookup('env','MYSQL_USER') | default('etherpad', true) }}"
mariadb_password: "{{ lookup('env','MYSQL_PASSWORD') | default('admin', true) }}"
etherpad_admin_password: "{{ lookup('env','ETHERPAD_ADMIN_PASSWORD') | default('admin', true) }}"
etherpad_admin_user: "{{ lookup('env','ETHERPAD_ADMIN_USER') | default('etherpad', true) }}"
etherpad_db_host: "{{ lookup('env','ETHERPAD_DB_HOST') | default('mariadb', true) }}"
state: present
```

### Actions
Next we'll need to create `actions` for our APB.  At a minimum, we'll need to create the `provision.yml` and `deprovision.yml` under the `playbooks` folder.

The `provision.yml` may look something like this:
```yml
- name: Provision My APB
  hosts: localhost
  gather_facts: false
  connection: local
  roles:
  - role: ansible.kubernetes-modules
    install_python_requirements: no
  - role: my-apb-openshift
    playbook_debug: false
```

And a simple `deprovision.yml` may look like this.
```yml
- name: Deprovision My APB
  hosts: localhost
  gather_facts: false
  connection: local
  vars:
    state: absent
  roles:
  - role: ansible.kubernetes-modules
    install_python_requirements: no
  - role: my-apb-openshift
    playbook_debug: false
```

### Updated Directory Structure 
We will also need to create the Ansible roles as specified in the actions. The below directory structure shows what it can look like:

```bash
my-apb/
├── apb.yml
├── Dockerfile
├── playbooks
│   └── deprovision.yml
│   └── provision.yml
└── roles
    └── my-apb-openshift
        ├── defaults
        │   └── main.yml
        ├── files
        │   └── <my-apb files>
        ├── README
        ├── tasks
        │   └── main.yml
        └── templates
            └── <template files>
```

### APB Prepare
If the `apb.yml` was edited at all, `apb prepare` must be ran to update the encoding of the spec file in the `Dockerfile`.

```bash
$ apb prepare
```

### Build
We can now build the APB by running from the parent directory:

```bash
$ docker build -t <docker-org>/my-apb .
```

### Deploy
We can now run the APB with:

```bash
$ docker run \
    -e "OPENSHIFT_TARGET=https://<oc-cluster-host>:<oc-cluster-port>" \
    -e "OPENSHIFT_TOKEN=<oc-token>" \
    <docker-org>/my-apb <action>
```
where `<action>` is either `provision` or `deprovision`.
