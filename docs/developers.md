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
### Spec File (Version 1.0)
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
$ apb build
```
or
```bash
$ apb build --tag <registry-prefix>/<docker-org>/my-apb
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

# Tips and Tricks

## Working with the restriced scc
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

## Using a ConfigMap within an APB
One common use case for ConfigMaps is when the parameters of an APB will be used within a configuration file of an application or service. The ConfigMap module allows you to mount a ConfigMap into a pod as a volume which can be used to store the config file. This approach allows you to also leverage the power Ansible's `template` module to create a ConfigMap out of APB paramters. The following is an example of creating a ConfigMap from a jinja template mounted into a pod as a volume.

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

# APB Spec Versioning
We are using semantic versioning with the format of x.y where x is a major release and y is a minor release.

## Major Version Bump
We will increment the major version whenever an API breaking change is introduced to the APB spec. Some examples include:
* Introduction/deletion of a required field
* Changing the yaml format
* New features

## Minor Version Bump
We will increment the minor version whenever a non-breaking change is introduced to the APB spec. Some examples include:
* Introduction/deletion of an optional field
* Spelling change
* Introduction of new options to an existing field
