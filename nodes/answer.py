
import requests


class AnswerNode(object):
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        

    def answer(self):
        req_str = self.kwargs['req_base'] + "channels/%s/answer" % self.kwargs['channel_id']
        status = requests.post(req_str, auth=(self.kwargs['username'], self.kwargs['password']))
        return status
