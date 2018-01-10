import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)) + '/../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from request import Request

class Apb_Directory(Request):

    def __init__(self, kwargs):
        super(Apb_Directory, self).__init__(kwargs)

    def _write_file(self, file_out, destination, force):
        self._touch(destination, force)
        with open(destination, 'w') as outfile:
            outfile.write(''.join(file_out))

    def _touch(self, fname, force):
        if os.path.exists(fname):
            os.utime(fname, None)
            if force:
                os.remove(fname)
                open(fname, 'a').close()
        else:
            open(fname, 'a').close()
