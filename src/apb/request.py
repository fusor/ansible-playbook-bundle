import base64
import requests
import urllib3

from requests.packages.urllib3.exceptions import InsecureRequestWarning
from openshift import client as openshift_client, config as openshift_config
from kubernetes import client as kubernetes_client, config as kubernetes_config
from kubernetes.client.rest import ApiException

# Disable insecure request warnings from both packages
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class Request(object):

    def __init__(self, kwargs):
        openshift_config.load_kube_config()
        self.token = openshift_client.configuration.api_key['authorization']
        self.host = openshift_client.configuration.host
        self.oapi = openshift_client.OapiApi()
        self.routing_prefix = "ansible-service-broker"

        self.route_list = self.oapi.list_namespaced_route('ansible-service-broker')
        if self.route_list.items == []:
            print("Didn't find OpenShift Ansible Broker route in namespace: " \
                  "ansible-service-broker. Trying openshift-ansible-service-broker")
            self.route_list = self.oapi.list_namespaced_route('openshift-ansible-service-broker')

        if self.route_list.items == []:
            print("Still failed to find a route to OpenShift Ansible Broker.")
            return

        self.args = kwargs

        print "init"

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
            return Exception("Could not find route to ansible-service-broker. "
                             "Use --broker or log into the cluster using \"oc login\"")

        self.auth_pass = self.args['basic_auth_password']
        self.auth_user = self.args['basic_auth_username']
        self.auth_header = self._auth_header()


    def _auth_header(self):
        if self.auth_user is not None and self.auth_pass is not None:
            self.headers = {'Authorization': "Basic " +
                       base64.b64encode("{0}:{1}".format(self.auth_user,
                                                         self.auth_pass))
                   }
        else:
            self.headers = {'Authorization': self.token}


    def relist_service_broker(self):
        response = requests.request("get",
                                    self.broker_resource_url,
                                    verify=self.args['verify'],
                                    headers=self.headers)

        if response.status_code != 200:
            errMsg = "Received non-200 status code while retrieving broker: " \
                     "{}\n".format(self.broker_name) + "Response body:\n" + \
                     str(response.text)
            return Exception(errMsg)

        spec = response.json().get('spec', None)
        if spec is None:
            errMsg = "Spec not found in broker reponse. Response body: \n{}".format(response.text)
            return Exception(errMsg)

        relist_requests = spec.get('relistRequests', None)
        if relist_requests is None:
            errMsg = "relistRequests not found within the spec of broker: " \
                     "{}\n".format(self.broker_name) + "Are you sure you are " \
                     "using a ServiceCatalog of >= v0.0.21?"
            return Exception(errMsg)

        inc_relist_requests = relist_requests + 1

        headers['Content-Type'] = 'application/strategic-merge-patch+json'
        response = requests.request(
            "patch",
            self.broker_resource_url,
            json={'spec': {'relistRequests': inc_relist_requests}},
            verify=self.args['verify'], headers=self.headers)

        if response.status_code != 200:
            errMsg = "Received non-200 status code while patching relistRequests of broker: " \
                     "{}\n".format(self.broker_name) + "Response body:\n{}".format(str(response.text))
            return Exception(errMsg)

        print("Successfully relisted the Service Catalog")


    def get_asb_route(self):
        for route in self.route_list.items:
            if 'asb' in route.metadata.name and 'etcd' not in route.metadata.name:
                asb_route = route.spec.host

        url = "%s/%s" % (asb_route, self.routing_prefix)
        if url.find("http") < 0:
            url = "https://" + url

        return url


    def list_apbs(self):
        url = "%s/v2/catalog" % self.route
        print("Contacting the ansible-service-broker at: %s" % url)

        response = requests.request("get", url, verify=self.args['verify'],
                                    headers=self.headers)

        if response.status_code != 200:
              print("Error: Attempt to list APBs in the broker returned " \
                    "status: %d" % response.status_code)
              return Exception("Unable to list APBs in Ansible Service Broker.")

        services = response.json()['services']

        if not services:
            print("No APBs found")
        elif self.args["output"] == 'json':
            self._print_json_list(services)
        elif self.args["verbose"]:
            self._print_verbose_list(services)
        else:
            self._print_list(services)


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
