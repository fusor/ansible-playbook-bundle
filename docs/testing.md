## Testing APB Image

### Why would we want to test the image?
The reason that we would want to be able to integration test APB's is that they have underlying images that could have been changed and would potentially cause the APB to fail. This means that to test the APB we would like to give the author the ability to verify certain actions by calling actions with default params.

### Design
The base APB entrypoint will learn the test action. The test action will be a test harness script *(This script will run pre-defined values for now, this should be configurable in the future)*.

To include the testing of an APB add to the layout and add files and example of the layout is 
```bash
my-apb/
├── apb.yml
├── Dockerfile
├── playbooks/
    └── provision.yml  
└── roles/
    └── ...
└── test/
    └── provision_default.yml # Will be the defaults that will be used for the provision request. The parameters that are required should have default values here.
    └── provision_verify.yml # Will be used verify the provision. This should be filled with whatever the APB author would want to verify.
```


### Running the test

To the run the test, you should only need to run ```oc run <name you want> --image <image> -- test```
