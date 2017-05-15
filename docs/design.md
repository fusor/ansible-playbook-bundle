# Ansible Playbook Bundle (APB) Spec File

Example:

```yaml
name: fusor/etherpad-apb
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
Or with an empty parameters field
```yaml
name: example/no-parameters 
description: Example showing no parameters
bindable: false
async: optional
parameters: []
```

> TODO: Explain specfile base64 encoding and label stamp

## Specifying Configuration Parameters

`parameters` section of the specfile; `ParameterObject` array

**ParameterObject**

Field Name | Type | Required | Default | Description
---|---|---|---|---
name | string| yes |  | The name of the parameter.
required| bool | no | true | Whether or not the parameter is required.  If `false` and no default is provided, will be omitted from the parameters passed to the APB.
description | string | yes | | A human readable description of the parameter.
type | string | yes | | Type of parameter. `bool`, `int`, `float`, `string`, are valid
default | bool,int,float,string|  no | | An optional default value for the parameter.


## Running Ansible Playbook Bundles

APBs are containers that are run with the following command:

`docker run $container_name $action $arguments`

* `container_name`

The name of the APB container, i.e. `apb/etherpad`

* `action`

One of the 4 possible actions an APB can take. At a minimum, an APB
must implement provision and deprovision.

```
* provision
* deprovision
* bind
* unbind
```

* `arguments`

Arguments in the form of a JSON payload that an APB may need to perform
a specified action. JSON is an `Arguments` object:

**Arguments**

Field Name | Description
---|---
instance_id | **Required** Service instance id. UUID string
answers | **Required.** JSON object containing key-value answers for parameter config
cluster | **Required.** `ClusterObject` containing targetted cluster information and credentials (TBD)

> TODO: ## Authentication section to better describe ClusterObject schema and what's included

> TODO: ## Dependencies! How is the container graph represented in a spec file. Is it necessary?
