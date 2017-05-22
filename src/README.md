# apb tooling

> NOTE: Project is still a WIP and rapidly changing.

`apb` is a tool for helping APB authors create, build, and publish
their APBs to container registries. It enforces best practices and takes
care of the details so they should be easy to deploy.

## Install

**System installation**:

`sudo pip install -r requirements.txt && sudo python setup.py install`

For non-priviledged installs such as virtualenvs, drop sudo.

**Development**:

`pip install -e $SRC_DIR` will install in editable mode.

## Commands

### Init

`apb init` is a helper that will generate a skeleton APB directory with
an `apb.yaml`, a `Dockerfile`, a `roles` directory, and a `playbooks` directory. 
`apb init` requires a name to be passed as an argument which will be used as the 
APB name.

#### Options:
```
`--org ORGANIZATION` specifies an organization name for the APB image on the `Dockerfile`.
`--async ASYNC_OPTION` specifies the asynchronous operation of the APB. Defaults to `optional`
         valid options are: ['required', 'optional', 'unsupported']
`--not-bindable` specifies if the APB will not be bindable by default. Defaults to `False`.
`--param PARAM_STRING`, `-p PARAM_STRING` Specifies which parameters to include by default in `apb.yaml`.
    `PARAM_STRING` contains four options to specify for a parameter separated by a comma. `name`, `type`, `description`, `default`.
    Ex. `apb init my_apb -p name=sample_name,default=foo,type=string,description="sample description"`
```
### Prepare

`apb prepare` is a helper that will update the `Dockerfile` with
your `apb.yaml` file encoded as a base64 label. This allows the spec
to be accessible to clients via registry APIs without the necessity of downloading
full images. For example, the [Ansible Service Broker](https://www.github.com/fusor/ansible-service-broker)
will use this data to build an inventory of available APBs in a given
registry and expose them to an Openshift or Kubernetes cluster.



By default, the CWD is used, but it will accept a directory location via
`--project=$LOCATION` as well.

Prepare also expects a specfile, `apb.yaml`, to exist at the project root.
[More on specfiles and expected contents.](https://github.com/fusor/ansible-playbook-bundle/blob/master/docs/design.md).

Following `apb prepare`, you should have a Dockerfile and a correctly
ID'd specfile. Build and publish this container to your preferred registry.
