## Testing APB Image

### Motivation
As the ecosystem of APBs grows we want to facilitate a means for performing a basic sanity check to ensure that an APB is working as the author intended. The basic concept is to package an integration test with the APB code which will contain all of the needed parameters for the actions that the test playbook will run. 

### Limitation Of Proposal
This proposal and subsequent examples are focusing on testing the provision action. We will be adding other actions in the future. 

The intention of this design is to check that an APB passes a basic sanity check before publishing to the service catalog. The initial proposal is to be used by CI or another process to check the APB before it is published. This proposal is not meant to be testing a live service. OpenShift provides the ability to test a live service using [liveness and readiness probes](https://docs.openshift.org/latest/dev_guide/application_health.html), which you can add when provisioning. 

### Requirements
* The existence of a test.yml in the playbooks directory.
```bash
my-apb/
├── ...
├── playbooks/
    ├── test.yml  
    └── ...
```

* This test.yml is intended to run the provision action at a minimum with some known values for a basic configuration. 
* To run the test, `oc run <deployment-name> --image=<image> --env "OPENSHIFT_TOKEN=< output of oc whoami -t >" --env "OPENSHIFT_TARGET=< OpenShift Cluster > -- test` Must be all you need to run the full the test. 
* Will have to use the pod status to determine if the action was successful or not.

#### Using Test during CI
We should be able to use `apb test` during CI to test the APB's during a rebuild of the images. Dependencies to run the integration testing during CI.

1. A cluster that is up and running and the CI server can interact with.
2. A user who is logged into the cluster and ability to run oc run.
3. Run the image using the oc command above and retrieve the status of the pod to determine pass and failure.
