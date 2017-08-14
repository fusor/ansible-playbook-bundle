## Testing APB Image

### Why would we want to test the image?
The reason that we would want to be able to integration test APB's is that they have underlying images that could have been changed and would potentially cause the APB to fail. This means that to test the APB we would like to give the author the ability to verify certain actions by calling actions with default params.

### Design
The base APB entrypoint will learn the test action. The test action will be a user defined playbook. 
To include the testing of an APB just add the playbook ```test.yml```
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

### Running the test
To the run the test, you should only need to run ```oc run <name you want> --image <image> -- test```

### Writing a ```test.yaml``` action
To orchastrate the testing of an APB it is suggested to use the include_vars and include_roles.
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
```


### Verify Roles
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
