
import time


class DtmfNode(object):
    def __init__(self, obj, options):
        self.vboard_obj = obj
        self.options = options


    def get_dtmf(self):
        self.vboard_obj.subscribe_event('ChannelDtmfReceived')
        while True:
            time.sleep(0.3)
            if self.vboard_obj.eventDict['ChannelDtmfReceived']['status']:
                digit = self.vboard_obj.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                self.vboard_obj.unsubscribe_event('ChannelDtmfReceived')
                break
        return digit
