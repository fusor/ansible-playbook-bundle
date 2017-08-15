## Testing APB Image

### Motivation
As the ecosystem of APBs grows we want to facilitate a means for performing a basic sanity check to ensure that an APB is working as the author intended. The basic concept is to package an integration test with the APB code which will contain all of the needed parameters for the actions that the test playbook will run. 
*Note: we are focusing on a basic provision to start other actions should be added in the future.*

### Design
The base APB entry point will learn the test action. The test action will be a user defined playbook. 
* To include the testing of an APB just add the playbook ```test.yml```
* The defaults for the test will be in the ```vars/```` directory of the playbooks.
* The ```verify_<name>``` role should be in the roles folder. Should be a normal [ansible role](http://docs.ansible.com/ansible/latest/playbooks_reuse_roles.html).
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

### Writing a ```test.yaml``` action
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

