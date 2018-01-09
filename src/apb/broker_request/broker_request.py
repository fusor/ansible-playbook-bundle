import base64
import docker
import os
import requests
import shutil
import sys
import urllib3

from openshift import client as openshift_client, config as openshift_config
from kubernetes import client as kubernetes_client, config as kubernetes_config
from kubernetes.client.rest import ApiException
from requests.packages.urllib3.exceptions import InsecureRequestWarning

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)) + '/../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from request import Request

class Broker_Request(Request):

    def __init__(self, kwargs):
        super(Broker_Request, self).__init__(kwargs)

        self._fetch_clients()

        self.routing_prefix = "ansible-service-broker"
        self.token = openshift_client.configuration.api_key['authorization']
        self.host = openshift_client.configuration.host
        self.oapi = openshift_client.OapiApi()
        self.v1api = kubernetes_client.CoreV1Api()

        try:
            self.route_list = self.oapi.list_namespaced_route('ansible-service-broker')
        except Exception:
            raise Exception("Could not find route to ansible-service-broker. "
                            "Use --broker or log into the cluster using \"oc login\"")

        if self.route_list.items == []:
            print("Didn't find OpenShift Ansible Broker route in namespace: " \
                  "ansible-service-broker. Trying openshift-ansible-service-broker")
            self.route_list = self.oapi.list_namespaced_route('openshift-ansible-service-broker')

        if self.route_list.items == []:
            print("Still failed to find a route to OpenShift Ansible Broker.")
            raise Exception("Could not find route to ansible-service-broker.")


        self._fetch_broker()
        self.auth_pass = self.args['basic_auth_password']
        self.auth_user = self.args['basic_auth_username']
        self.verify = self.args['verify']
        self.auth_header = self._auth_header()

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


    def _fetch_broker(self):
        '''
        Gather Broker information.
        '''
        # TODO: Improve error checking by verifing connection to the route
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

        print self.route


    def _fetch_clients(self):
        try:
            openshift_config.load_kube_config()
        except Exception as e:
            raise e

        try:
            self.docker_client = docker.DockerClient(base_url='unix://var/run/docker.sock', version='auto')
        except Exception as e:
            raise e
