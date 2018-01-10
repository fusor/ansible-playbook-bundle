# TODO: Dump a stacktrace with an expection to show where a command failed
#
# import logging
# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)
#
class Request(object):
    '''Common functions and variables across all types of requests'''

    def __init__(self, kwargs):
        self.args = kwargs

        self.apb_spec_file = 'apb.yml'
