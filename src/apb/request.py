import base64
import docker
import os
import requests
import shutil
import urllib3

from requests.packages.urllib3.exceptions import InsecureRequestWarning

# Disable insecure request warnings from both packages
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class Request(object):

    def __init__(self, kwargs):
        self.args = kwargs

        self.apb_spec_file = 'apb.yml'


    def _load_spec_dict(self, spec_path):
        with open(spec_path, 'r') as spec_file:
            return YAML().load(spec_file.read())


    def _load_spec_str(self, spec_path):
        with open(spec_path, 'r') as spec_file:
            return spec_file.read()


    def _get_spec(self, project, output="dict"):
        spec_path = os.path.join(project, self.apb_spec_file)

        if not os.path.exists(spec_path):
            raise Exception('ERROR: Spec file: [ %s ] not found' % spec_path)

        try:
            if output == 'string':
                spec = self._load_spec_str(spec_path)
            else:
                spec = self._load_spec_dict(spec_path)
        except Exception as e:
            print('ERROR: Failed to load spec!')
            raise e

        return spec


    def _get_registry_service_ip(self, namespace, svc_name):
        ip = None
        try:
            service = self.v1api.read_namespaced_service(namespace=namespace, name=svc_name)
            if service is None:
                print("Couldn't find docker-registry service in namespace default. Erroring.")
                return None
            if service.spec.ports == []:
                print("Service spec appears invalid. Erroring.")
                return None
            ip = service.spec.cluster_ip + ":" + str(service.spec.ports[0].port)
            print("Found registry IP at: " + ip)

        except Self.V1apiException as e:
            print("Exception occurred trying to find %s service in namespace %s: %s" % (svc_name, namespace, e))
            return None
        return ip


    def load_dockerfile(df_path):
        with open(df_path, 'r') as dockerfile:
            return dockerfile.readlines()


    def _load_makefile(self, apb_dict, params):
        env = Environment(loader=FileSystemLoader(DAT_PATH), trim_blocks=True)
        template = env.get_template(EX_MAKEFILE)

        if not params:
            params = []

        return template.render(apb_dict=apb_dict, params=params)


    def _load_example_specfile(self, apb_dict, params):
        env = Environment(loader=FileSystemLoader(DAT_PATH), trim_blocks=True)
        template = env.get_template(EX_SPEC_FILE)

        if not params:
            params = []

        return template.render(apb_dict=apb_dict, params=params)


    def _write_file(self, file_out, destination, force):
        touch(destination, force)
        with open(destination, 'w') as outfile:
            outfile.write(''.join(file_out))


    def relist_service_broker(self):
        '''
        Relist the ansible-service-broker in the catalog
        '''

        response = requests.request("get",
                                    self.broker_resource_url,
                                    verify=self.verify,
                                    headers=self.headers)

        if response.status_code != 200:
            errMsg = "Received non-200 status code while retrieving broker: " \
                     "{}\n".format(self.broker_name) + "Response body:\n" + \
                     str(response.text)
            raise Exception(errMsg)

        spec = response.json().get('spec', None)
        if spec is None:
            errMsg = "Spec not found in broker reponse. Response body: \n{}".format(response.text)
            raise Exception(errMsg)

        relist_requests = spec.get('relistRequests', None)
        if relist_requests is None:
            errMsg = "relistRequests not found within the spec of broker: " \
                     "{}\n".format(self.broker_name) + "Are you sure you are " \
                     "using a ServiceCatalog of >= v0.0.21?"
            raise Exception(errMsg)

        inc_relist_requests = relist_requests + 1

        headers['Content-Type'] = 'application/strategic-merge-patch+json'
        response = requests.request(
            "patch",
            self.broker_resource_url,
            json={'spec': {'relistRequests': inc_relist_requests}},
            verify=self.verify, headers=self.headers)

        if response.status_code != 200:
            errMsg = "Received non-200 status code while patching relistRequests of broker: " \
                     "{}\n".format(self.broker_name) + "Response body:\n{}".format(str(response.text))
            raise Exception(errMsg)

        print("Successfully relisted the Service Catalog")


    def get_asb_route(self):
        '''
        Find the ansible-service-broker route.

        TODO: Add Kubernetes support by searching for an endpoint
        '''

        for route in self.route_list.items:
            if 'asb' in route.metadata.name and 'etcd' not in route.metadata.name:
                asb_route = route.spec.host

        url = "%s/%s" % (asb_route, self.routing_prefix)
        if url.find("http") < 0:
            url = "https://" + url

        return url


    def apb_push(self):
        '''
        Push an apb to the catalog.
        '''
        project = self.args['base_path']
        spec = self._get_spec(project, 'string')
        dict_spec = self._get_spec(project, 'dict')
        blob = base64.b64encode(spec)
        data_spec = {'apbSpec': blob}
        print(spec)

        if self.args['openshift']:
            namespace = self.args['reg_namespace']
            service = self.args['reg_svc_name']

            # Assume we are using internal registry, no need to push to broker
            registry = self._get_registry_service_ip(namespace, service)
            if registry is None:
                print("Failed to find registry service IP address.")
                raise Exception("Unable to get registry IP from namespace %s" % namespace)
            tag = registry + "/" + self.args['namespace'] + "/" + dict_spec['name']
            print("Building image with the tag: " + tag)

            try:
                self.docker_client.images.build(path=project, tag=tag, dockerfile=self.args['dockerfile'])
                bearer = 'Bearer %s' % self.token
                self.docker_client.login(username="unused", password=bearer, registry=registry, reauth=True)
                self.docker_client.images.push(tag)
                print("Successfully pushed image: " + tag)
                self.bootstrap()
            except docker.errors.DockerException:
                print("Error accessing the docker API. Is the daemon running?")
                raise
            except docker.errors.APIError:
                print("Failed to login to the docker API.")
                raise

        else:
            url = "%s/v2/apb" % self.route
            response = requests.request("post", url, data=data_spec,
                                        verify=self.verify,
                                        headers=self.headers)

            if response.status_code != 200:
                print("Error: Attempt to add APB to the Broker returned status: %d" % response.status_code)
                print Exception("Unable to add APB to Ansible Service Broker.")
                raise

            print("Successfully added APB to Ansible Service Broker")

        if not self.args['no_relist']:
            self.relist_service_broker()

    def bootstrap(self):
        url = "%s/v2/bootstrap" % self.route
        response = requests.request("post", url, verify=self.verify,
                                    headers=self.headers)

        if response.status_code != 200:
            print("Error: Attempt to bootstrap Broker returned status: %d" % response.status_code)
            print("Unable to bootstrap Ansible Service Broker.")
            raise

        print("Successfully bootstrapped Ansible Service Broker")


    def apb_init(self):
        current_path = self.args['base_path']
        bindable = self.args['bindable']
        async = self.args['async']
        dockerhost = self.args['dockerhost']
        skip = {
            'provision': self.args['skip-provision'],
            'deprovision': self.args['skip-deprovision'],
            'bind': self.args['skip-bind'] or not self.args['bindable'],
            'unbind': self.args['skip-unbind'] or not self.args['bindable'],
            'roles': self.args['skip-roles']
        }

        apb_tag_arr = self.args['tag'].split('/')
        apb_name = apb_tag_arr[-1]
        app_org = apb_tag_arr[0]
        if apb_name.lower().endswith("-apb"):
            app_name = apb_name[:-4]
        else:
            app_name = apb_name

        description = "This is a sample application generated by apb init"

        apb_dict = {
            'name': apb_name,
            'app_name': app_name,
            'app_org': app_org,
            'description': description,
            'bindable': bindable,
            'async': async,
            'dockerhost': dockerhost
        }

        project = os.path.join(current_path, apb_name)

        if os.path.exists(project):
            if not self.args['force']:
                raise Exception('ERROR: Project directory: [%s] found and force option not specified' % project)
            shutil.rmtree(project)

        print("Initializing %s for an APB." % project)

        os.mkdir(project)

        spec_path = os.path.join(project, SPEC_FILE)
        dockerfile_path = os.path.join(os.path.join(project, DOCKERFILE))
        makefile_path = os.path.join(os.path.join(project, MAKEFILE))

        specfile_out = load_example_specfile(apb_dict, [])
        write_file(specfile_out, spec_path, self.args['force'])

        dockerfile_out = load_dockerfile(EX_DOCKERFILE_PATH)
        write_file(dockerfile_out, dockerfile_path, self.args['force'])

        makefile_out = load_makefile(apb_dict, [])
        write_file(makefile_out, makefile_path, self.args['force'])

        generate_playbook_files(project, skip, apb_dict)
        print("Successfully initialized project directory at: %s" % project)
        print("Please run *apb prepare* inside of this directory after editing files.")
