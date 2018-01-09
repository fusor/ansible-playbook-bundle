import base64
import os
import requests

from ruamel.yaml import YAML

from broker_request import Broker_Request


class Apb_Push(Broker_Request):
    '''
    Push an apb to the catalog.
    '''
    def __init__(self, kwargs):
        super(Apb_Push, self).__init__(kwargs)
        self.apb_push()


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


    def _load_spec_dict(self, spec_path):
        with open(spec_path, 'r') as spec_file:
            return YAML().load(spec_file.read())


    def _load_spec_str(self, spec_path):
        with open(spec_path, 'r') as spec_file:
            return spec_file.read()


    def load_dockerfile(df_path):
        with open(df_path, 'r') as dockerfile:
            return dockerfile.readlines()


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


    def apb_push(self):
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
