import requests

from broker_request import Broker_Request


class Apb_Bootstrap(Broker_Request):
    '''
    Senf a bootstrap request to the ansible-service-broker.
    '''

    def __init__(self, kwargs):
        super(Apb_Bootstrap, self).__init__(kwargs)
        self.apb_bootstrap()


    def apb_bootstrap(self):
        url = "%s/v2/bootstrap" % self.route
        response = requests.request("post", url, verify=self.verify,
                                    headers=self.headers)

        if response.status_code != 200:
            print("Error: Attempt to bootstrap Broker returned status: %d" % response.status_code)
            print("Unable to bootstrap Ansible Service Broker.")
            raise

        print("Successfully bootstrapped Ansible Service Broker")
