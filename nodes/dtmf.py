
import time


class DtmfNode(object):
    def __init__(self, obj, options):
        self.obj = obj
        self.options = options


    def get_dtmf(self):
        self.obj.subscribe_event('ChannelDtmfReceived')
        while True:
            time.sleep(0.3)
            if self.obj.eventDict['ChannelDtmfReceived']['status']:
                digit = self.obj.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                self.obj.unsubscribe_event('ChannelDtmfReceived')
                break

        return digit


    def get_multiple_dtmf(self, length):
        digit = ''
        self.obj.subscribe_event('ChannelDtmfReceived')
        while True:
            time.sleep(0.3)
            if self.obj.eventDict['ChannelDtmfReceived']['status']:
                dtmf = self.obj.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                digit += dtmf
                self.obj.eventDict['ChannelDtmfReceived']['status'] = False
                if len(digit) == length:
                    self.obj.unsubscribe_event('ChannelDtmfReceived')
                    break

        return digit