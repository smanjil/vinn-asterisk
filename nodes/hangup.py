
import requests


class HangupNode(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        

    def hang_up(self):
        req_str = self.kwargs['req_base'] + "channels/%s" % self.kwargs['channel_id']
        status = requests.delete(req_str, auth=(self.kwargs['username'], self.kwargs['password']))
        return status
