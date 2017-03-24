
import uuid
import requests
import time
from dtmf import DtmfNode


class RecordNode(object):
    def __init__(self, obj, **kwargs):
        self.obj = obj
        self.kwargs = kwargs


    def start_record(self):
        self.obj.subscribe_event('RecordingFinished')
        fname = uuid.uuid1()
        req_str = self.kwargs['req_base'] + "channels/{0}/record?name={1}&format={2}&maxDurationSeconds={3}&ifExists={4}&beep={5}&terminateOn={6}" \
            .format(self.kwargs['channel_id'], fname, 'wav', 10, 'overwrite', True, 'any')
        requests.post(req_str, auth=(self.kwargs['username'], self.kwargs['password']))

        # dtmf handling for record termination
        dtmf = DtmfNode(self.obj, options=['*', '#'])
        dtmf_digit = dtmf.get_dtmf()
        while dtmf_digit:
            time.sleep(0.3)
            if dtmf_digit == '#':
                self.stop_record(fname)
                self.obj.unsubscribe_event('RecordingFinished')
                break

        return fname


    def stop_record(self, fname):
        req_str = self.kwargs['req_base'] + "recordings/live/{0}/stop".format(fname)
        requests.post(req_str, auth=(self.kwargs['username'], self.kwargs['password']))
