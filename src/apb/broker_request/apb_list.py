import requests

from broker_request import Broker_Request


class Apb_List(Broker_Request):
    '''
    List the apbs in the catalog.
    '''
    def __init__(self, kwargs):
        super(Apb_List, self).__init__(kwargs)
        self.apb_list()


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
                plan_bind_params = plan['schemas']['service_binding']['create']['parameters']['propertie']
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


    def apb_list(self):
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
