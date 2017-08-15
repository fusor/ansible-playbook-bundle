## Testing APB Image

### Motivation
As the ecosystem of APBs grows we want to facilitate a means for performing a basic sanity check to ensure that an APB is working as the author intended. The basic concept is to package an integration test with the APB code which will contain all of the needed parameters for the actions that the test playbook will run. 
*Note: we are focusing on a basic provision to start other actions should be added in the future.*

### Design
The base APB entry point will be able to find and run the test action. The test action will be a user defined playbook. 

* To include the testing of an APB just add the playbook `test.yml`
* The defaults for the test will be in the `vars/` directory of the playbooks.
* The `verify_<name>` role should be in the roles folder. Should be a normal [ansible role](http://docs.ansible.com/ansible/latest/playbooks_reuse_roles.html).
```bash
my-apb/
├── apb.yml
├── Dockerfile
├── playbooks/
    ├── test.yaml  
    └── vars/
        └── test_defaults.yaml

└── roles/
    ├── ...
    └── verify_apb_role
        ├── defaults
             └── defaults.yml
        └── tasks  
            └── main.yml
```

### Writing a `test.yaml` action
To orchestrate the testing of an APB it is suggested to use the [include_vars](http://docs.ansible.com/ansible/latest/include_vars_module.html) and [include_role](http://docs.ansible.com/ansible/latest/include_role_module.html) modules.
Example
```yaml
 - name: test rhscl-postgresql-apb
   hosts: localhost
   gather_facts: false
   connection: local

   # Load the ansible kubernetes modules
   roles:
   - role: ansible.kubernetes-modules
     install_python_requirements: no
 
   post_tasks:
   # Include the default values needed for provision from test role.
   - name: Load default variables for testing
     include_vars: test_defaults.yaml
   - name: Run the provisio role.
     include_role:
       name: rhscl-postgresql-apb-openshift
   - name: Verify the provision.
     include_role:
       name: verify_rhscl-postgresql-apb-openshift
```


### Verify Roles
Verify roles will allow the author to determine if the provision has failed or succeeded. 
Example verify role.
```yaml
---
 - name: url check for media wiki
   uri:
     url: "http://{{ route.route.spec.host }}"
     return_content: yes
   register: webpage
   failed_when: webpage.status != 200
```

### Test Results
The APB should be able to save test results so that an external caller can retrieve the results. This should behave very similar to [asb_encode_binding](https://github.com/fusor/ansible-asb-modules/blob/master/library/asb_encode_binding.py). 
**Implementation changes to be made**: 

- Create new module: `save_test_result` this will save the test results to `/var/tmp/test-result`. Should follow a format for the file such as 
```text
0
success
```
or 
```text
1
<message>
```
- Update [entrypoint.sh](https://github.com/fusor/apb-examples/blob/master/apb-base/files/usr/bin/entrypoint.sh) to wait with test-results were created.
- Create `test-retrieval-init` to follow the same pattern as [bind-init](https://github.com/fusor/apb-examples/blob/master/apb-base/files/usr/bin/bind-init).
- Create `test-retrieval` script that will be used like [broker-bind-creds](https://github.com/fusor/apb-examples/blob/master/apb-base/files/usr/bin/broker-bind-creds) to retrieve the test results from the pod. 

Example verify role with new module
```yaml
---
 - name: url check for media wiki
   uri:
     url: "http://{{ route.route.spec.host }}"
     return_content: yes
   register: webpage
   
  - name: Save failure for the web page
    asb_save_test_result:
      fail: true
      msg: "Could not reach route and retrieve a 200 status code. Recieved status - {{ webpage.status }}"
    when: webpage.status != 200
  
  - fail:
      msg: "Could not reach route and retrieve a 200 status code. Recieved status - {{ webpage.status }}"
    when: webpage.status != 200
  
  - name: Save test pass
    asb_save_test_result:
      fail: false
    when: webpage.status == 200
```

### Running Test And Getting Results
We will add a porcelain command, `apb test`. 
**Implementation changes to be made**: 

* Will build the image if it is in an APB's root directory, and run the test action. 
* Internally it will run something similar to `oc run <name you want> --image <image> --env "OPENSHIFT_TOKEN=<token>" --env "OPENSHIFT_TARGET=<target>" -- test`.
* It will be responsible for pulling out the test results from the test results file. This will use the `test-retrieval` script.
* Will print the results to the screen.


### Using Test during CI
We should be able to use `apb test` during CI to test the APB's during a rebuild of the images. Dependencies to run the integration testing during CI.

1. A cluster that is up and running and the CI server can interact with.
2. APB tool is installed
3. APB to be tested is checked out on the CI server.
