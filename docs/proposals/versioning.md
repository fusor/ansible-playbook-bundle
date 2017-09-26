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
* APB with version 1.y works with broker 1.y.z
* Any minor changes to the spec bumps APB minor version and an associated minor bump for broker
*
### Broker Source changes
* Move version.go into its own version pkg?
* in adapter.go run a check if majorVersion matches brokerMajorVersion
* Do not add image if major versions don't match
