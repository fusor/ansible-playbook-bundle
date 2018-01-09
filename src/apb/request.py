import base64
import docker
import os
import requests
import urllib3

from ruamel.yaml import YAML
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from openshift import client as openshift_client, config as openshift_config
from kubernetes import client as kubernetes_client, config as kubernetes_config
from kubernetes.client.rest import ApiException

# Disable insecure request warnings from both packages
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class Request(object):

    def __init__(self, kwargs):
        self._fetch_clients()

        self.apb_spec_file = 'apb.yml'

        self.routing_prefix = "ansible-service-broker"
        self.token = openshift_client.configuration.api_key['authorization']
        self.host = openshift_client.configuration.host
        self.oapi = openshift_client.OapiApi()
        self.v1api = kubernetes_client.CoreV1Api()

        self.route_list = self.oapi.list_namespaced_route('ansible-service-broker')
        if self.route_list.items == []:
            print("Didn't find OpenShift Ansible Broker route in namespace: " \
                  "ansible-service-broker. Trying openshift-ansible-service-broker")
            self.route_list = self.oapi.list_namespaced_route('openshift-ansible-service-broker')

        if self.route_list.items == []:
            print("Still failed to find a route to OpenShift Ansible Broker.")
            raise Exception("Could not find route to ansible-service-broker.")

        self.args = kwargs
        self._fetch_broker()

        self.auth_pass = self.args['basic_auth_password']
        self.auth_user = self.args['basic_auth_username']
        self.verify = self.args['verify']

        self.auth_header = self._auth_header()


    def _fetch_broker(self):
        '''
        Gather Broker information.
        '''
        if 'broker_name' in self.args:
            self.broker_name = self.args['broker_name']
            self.broker_resource_url = "{}/apis/servicecatalog.k8s.io/v1beta1/clusterservicebrokers/{}".format(self.host, self.broker_name)

        if self.args['broker'] is None:
            self.route = self.get_asb_route()
        else:
            self.route = self.args['broker']

        if not self.route.endswith(self.routing_prefix):
            if not self.route.endswith('/'):
                self.route = "%s/" % self.route
            self.route = "%s%s" % (self.route, self.routing_prefix)

        # TODO: Improve error checking by verifing connection to the route
        if self.route is None:
            raise Exception("Could not find route to ansible-service-broker. "
                             "Use --broker or log into the cluster using \"oc login\"")


    def _fetch_clients(self):
        try:
            openshift_config.load_kube_config()
        except Exception as e:
            raise e

        try:
            self.docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock', version='auto')
        except Exception as e:
            raise e


    def _auth_header(self):
        '''
        Create the authorization header based on the auth type.
        '''

        if self.auth_user is not None and self.auth_pass is not None:
            self.headers = {'Authorization': "Basic " +
                       base64.b64encode("{0}:{1}".format(self.auth_user,
                                                         self.auth_pass))
                   }
        else:
            self.headers = {'Authorization': self.token}


    def _print_json_list(self, services):
        print(json.dumps(services, indent=4, sort_keys=True))


    def _print_service(self, service):
        cmap = ruamel.yaml.comments.CommentedMap()

        if 'name' in service:
            cmap['name'] = service['name']
        if 'id' in service:
            cmap['id'] = service['id']
        if 'description' in service:
            cmap['description'] = service['description']
        if 'bindable' in service:
            cmap['bindable'] = service['bindable']
        if 'metadata' in service:
            cmap['metadata'] = service['metadata']
        if 'plans' in service:
            cmap['plans'] = _pretty_plans(service['plans'])

        print(ruamel.yaml.dump(cmap, Dumper=ruamel.yaml.RoundTripDumper))


    def _pretty_plans(self, plans):
        pp = []
        if plans is None:
            return
        for plan in plans:
            cmap = ruamel.yaml.comments.CommentedMap()
            if 'name' in plan:
                cmap['name'] = plan['name']
            if 'description' in plan:
                cmap['description'] = plan['description']
            if 'free' in plan:
                cmap['free'] = plan['free']
            if 'metadata' in plan:
                cmap['metadata'] = plan['metadata']

            try:
                plan_params = plan['schemas']['service_instance']['create']['parameters']['properties']
            except KeyError:
                plan_params = []

            cmap['parameters'] = plan_params

            try:
                plan_bind_params = plan['schemas']['service_binding']['create']['parameters']['properties']
            except KeyError:
                plan_bind_params = []

            cmap['bind_parameters'] = plan_bind_params

            pp.append(cmap)
        return pp


    def _print_list(self, services):
        max_id = 10
        max_name = 10
        max_desc = 10

        for service in services:
            max_id = max(max_id, len(service["id"]))
            max_name = max(max_name, len(service["name"]))
            max_desc = max(max_desc, len(service["description"]))

        template = "{id:%d}{name:%d}{description:%d}" % (max_id + 2, max_name + 2, max_desc + 2)
        print(template.format(id="ID", name="NAME", description="DESCRIPTION"))
        for service in sorted(services, key=lambda s: s['name']):
            print(template.format(**service))


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


    def apb_list(self):
        '''
        List the apbs in the catalog.
        '''

        url = "%s/v2/catalog" % self.route
        print("Contacting the ansible-service-broker at: %s" % url)

        response = requests.request("get", url, verify=self.verify,
                                    headers=self.headers)

        if response.status_code != 200:
              print("Error: Attempt to list APBs in the broker returned " \
                    "status: %d" % response.status_code)
              raise Exception("Unable to list APBs in Ansible Service Broker.")

        services = response.json()['services']

        if not services:
            print("No APBs found")
        elif self.args["output"] == 'json':
            self._print_json_list(services)
        elif self.args["verbose"]:
            self._print_verbose_list(services)
        else:
            self._print_list(services)


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
