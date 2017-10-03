## Plan for versioning APBs

### Current status:
* Currently all APBs are 0.1.0
  * This is stored in a label on the image titled “com.redhat.apb.version”
* Plan is to bump all APBs to a newer version to coincide with 3.7 Broker

### Questions:
* Should this be a major version bump? I.e. 1.0.0, or minor would be 0.2.0
* Do we tag the images with the version of the broker or APB spec version? Should they match?

### Thoughts:
* Makes sense to do a major version bump because the version has not changed since we were ansibleapp.
* Since the ‘plan’ format of the APB is not likely to change anytime soon it would make sense to establish the schema of the spec in a major bump. There are still some new APB developers who find old examples and try to use it without plans.
* 1.x.x APBs work on ASB/OC 3.7
* 0.x.x APBs are < ASB 3.6 
* Image tags should match whatever version number we choose. This would be a pro for versioning APBs in the same vein as ASB. i.e. 3.7 ASB can launch images tagged with 3.7.
* Could introduce minor version bump prior to 3.7 release

### Versioning use cases
* Bindable apps and broker support
* Post 3.7 we intend to use ‘launch_apb_on_bind’ which means that binding functionality will completely change.
  * Broker should be able to support old binding mechanism with <1.X.X APBs and all 1.X.X APBs should follow new binding format.
* Changes to APB spec
  * As the APB spec grows and the OSB spec changes we will need to continually change the APB spec. Locking down the spec to a versioning format where minor version bumps won’t break functionality will help as we grow and more people adopt the APB spec.


### Implementation Suggestion:
* We change APB version to x.y
* We bump APB version to 1.0
* Broker has configured acceptable range of APB version.
* Broker does a check if APB version is in acceptable range during validation of bootstrap.
* Broker version is NOT tied directly to APB spec version.

### Broker Source changes
* Move version.go into its own version pkg including apbversion.go
* in registry.go run a check if version is in acceptable range on the spec file
* Do not validate image if version is not in acceptable range.

### Example of a breaking change - Major Version Bump
* Changing the yaml format
* Addition/deletion of required fields

### Example of a non-breaking change - Minor Version Bump
* Spelling change of a field
* Addition/deletion of optional fields
* Additon/deltions of options to an optional/required field
