## Testing Implementation
This document will describe the steps taken to make [testing](testing.md) APB's easier in for APB authors. 

This is highly in flux and we should not be tied to this design if we find problems with it later.

#### Goals
* To make the development of `test.yml` easier.
* To give an overview of how I will implement the first example APB for testing.

#### Design
The base APB entry point will be able to find and run the test action. The test action will be a user defined playbook. 

* To include the testing of an APB just add the playbook `test.yml`
* The defaults for the test will be in the `vars/` directory of the playbooks.
* The `verify_<name>` role should be in the roles folder. Should be a normal [ansible role](http://docs.ansible.com/ansible/latest/playbooks_reuse_roles.html).
```bash
my-apb/
├── apb.yml
├── Dockerfile
├── playbooks/
    ├── test.yml  
    └── vars/
        └── test_defaults.yml

└── roles/
    ├── ...
    └── verify_apb_role
        ├── defaults
             └── defaults.yml
        └── tasks  
            └── provision.yml # specify the action that is being verified.
```

#### Writing a `test.yml` action
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
     include_vars: test_defaults.yml
   - name: Run the provisio role.
     include_role:
       name: rhscl-postgresql-apb-openshift
   - name: Verify the provision.
     include_role:
       name: verify_rhscl-postgresql-apb-openshift
       task_from: provision # this is the specific task file name provision.
```


#### Verify Roles
Verify roles will allow the author to determine if the provision has failed or succeeded. Verify roles could use 
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

#### Test Results
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

#### Running Test And Getting Results
We will add a porcelain command, `apb test`. 
**Implementation changes to be made**: 

* Will build the image if it is in an APB's root directory, and run the test action. 
* Internally it will run something similar to `oc run <name you want> --image <image> --env "OPENSHIFT_TOKEN=<token>" --env "OPENSHIFT_TARGET=<target>" -- test`.
* It will be responsible for pulling out the test results from the test results file. This will use the `test-retrieval` script.
* Will print the results to the screen.






