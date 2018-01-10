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

# TODO: Add logging everywhere to show progress with the apb command
# and to help debug where a problem occured
class Request(object):
    '''Common functions and variables across all types of requests'''

    def __init__(self, kwargs):
        self.args = kwargs

        self.apb_spec_file = 'apb.yml'


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
