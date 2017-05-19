# Developer Guide

## APB Examples
For completed APB examples, visit [APB Examples Repo](https://github.com/fusor/apb-examples) .

## Creating Ansible Playbook Bundles (APBs)

### APB Init
In order to create an APB, you will need to start with a skeleton APB directory structure.  The layout of the [directory structure](design.md#directory-structure) is shown in the [design](design.md) document.

You may create the directory structure yourself, or you can use the `apb init` command to create a simple skeleton structure, and modify it to your needs.  You will need to specify the name of your APB as a minimum input.  Visit the [APB Tooling README](https://github.com/fusor/ansible-playbook-bundle/blob/master/src/README.md) for more information.

Running the `apb init` will create a APB directory structure shown below:
```bash
$ apb init my-apb

$ tree my-apb
my-apb/
├── apb.yml
├── Dockerfile
├── playbooks/
└── roles/
```
### Spec File
The `apb init` will auto generate a spec file.  You must edit this spec file to fit your application. The following is the spec file for `etherpad-apb`.  More examples can be found in the [apb-examples repo](https://github.com/fusor/apb-examples)

```yml
name: apb/etherpad-apb
description: Note taking web application
bindable: true
async: optional
parameters:
  - name: hostport
    description: The host TCP port as the external endpoint
    type: int
    default: 9001
  - name: db_user
    description: Database User
    type: string
  - name: db_pass
    description: Database Password
    type: string
  - name: db_name
    description: Database Name
    type: string
  - name: db_host
    description: Database service hostname/ip
    default: mariadb
    type: string
  - name: db_port
    description: Database service port
    type: int
    default: 3306
```

##### Spec File Parameters
`parameters` section of the specfile; `ParameterObject` array

Field Name | Type | Required | Default | Description
---|---|---|---|---
name | string| yes |  | The name of the parameter.
required| bool | no | true | Whether or not the parameter is required.  If `false` and no default is provided, will be omitted from the parameters passed to the APB.
description | string | yes | | A human readable description of the parameter.
type | string | yes | | Type of parameter. `bool`, `int`, `float`, `string`, are valid
default | bool,int,float,string|  no | | An optional default value for the parameter.

### Actions
Next we'll need to create `actions` for our APB.  At a minimum, we'll need to create the `provision.yml` and `deprovision.yml` under the `playbooks` folder.

The `provision.yml` may look something like this:
```yml
- name: my-apb application
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
- hosts: localhost
  gather_facts: false
  connection: local
  tasks:
  - name: Delete my-apb project
    command: oc delete project my-apb
```

We will also need to create the Ansible roles as specified in the actions. The below directory structure shows what it can look like:

```bash
$ tree my-apb
my-apb/
├── apb.yml
├── Dockerfile
├── playbooks
│   └── provision.yml
│   └── deprovision.yml
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

### Build
We can now build the APB by running from the parent directory:

```bash
$ cd my-apb
$ docker build -t <docker-org>/my-apb .
```

### Deploy
We can now run the APB with:

```bash
$ docker run \
    -e "OPENSHIFT_TARGET=https://<oc-cluster-host>:<oc-cluster-port>" \
    -e "OPENSHIFT_USER=admin" \
    -e "OPENSHIFT_PASS=admin" \
    <docker-org>/my-apb <action>
```
where `<action>` is either `provision` or `deprovision`.


#### Adding parameters to an Ansible playbook bundle project

It is typical for containers to be designed with an entrypoint that takes parameters at run time for last-second configuration, allowing you to make generic containers rather than having to rebuild every time you want to change settings. To pass variables into an APB, you will need to escape the variable substitution in your `.yml` files. For example:

```yml
services:
  etherpad:
    [...]
    environment:
      - "DATABASE_USER={{ '{{ database_user }}' }}"
      - "DATABASE_PASSWORD={{ '{{ database_password }}' }}"
```

The above expects the `database_user` and `database_password` variables to be defined.

The apb-base entrypoint script will pass arguments through to the playbook, so in the example above, you could run an APB with the arguments:

```bash
$ docker run \
    [...] \
    <docker-org>/my-apb <action> \
    --extra-vars '{"database_user": "myuser", "database_password": "mypassword", "namespace":"my-apb"}'
```
and they will be passed to the `provision.yml`.
