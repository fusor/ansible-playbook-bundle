import requests

from broker_request import Broker_Request


class Apb_Relist(Broker_Request):
    '''
    Relist the apbs in the catalog.
    '''

    def __init__(self, kwargs):
        super(Apb_Relist, self).__init__(kwargs)
        self.apb_relist()


    def apb_relist(self):
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
