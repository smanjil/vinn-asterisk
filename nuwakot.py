# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import requests
import websocket
import json
import threading
import time
import uuid
import arrow
from models import GeneralizedDialplan, Services, GeneralizedDataIncoming, IncomingLog

server_addr = 'localhost'
app_name = 'hello-world'
username = 'asterusr'
password = 'asterusrkopass37'
req_base = "http://%s:8088/ari/" % server_addr


class VNuwakot(threading.Thread):
    def __init__(self, channel_id, dialplan, incoming_number, module_id, exten, service_name, org_id, allocated_channels, channels_inuse):
        super(VNuwakot, self).__init__()
        self.eventDict = {}
        self.channel_id = channel_id
        self.incoming_number = incoming_number
        self.module_id = module_id
        self.service_name = service_name
        self.org_id = org_id
        self.exten = exten
        self.allocated_channels = allocated_channels
        self.channels_inuse = channels_inuse
        self.output = {}
        self.playbackCompleted = False
        self.fname = ''

    def run(self):
        if self.channels_inuse < self.allocated_channels:
            req_str = req_base + "channels/%s/answer" % self.channel_id
            a = requests.post(req_str, auth=(username, password))
            if a.status_code == 204:
                self.channels_inuse += 1
                query = Services.update(channels_inuse = self.channels_inuse).where(Services.extension == self.exten)
                query.execute()
                print self.allocated_channels, self.channels_inuse
        else:
            # hang up
            req_str = req_base + "channels/%s" % channel_id
            requests.delete(req_str, auth=(username, password))

        self.output['playbackCompleted'] = self.playbackCompleted
        self.output['recordedFileName'] = self.fname

        #step 3
        def Menu1():
            pass

        #step 6
        def Menu2():
            pass

        # step1 - Play welcome message
        # Namaskar Nuwakot Hospital ko IVR sewa ma yaha lai swagat cha
        self.subscribe_event('PlaybackFinished')
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'nuwakot/1'))
        requests.post(req_str, auth=(username, password))

        while True:
            time.sleep(0.3)
            if self.eventDict['PlaybackFinished']['status']:
                self.unsubscribe_event('PlaybackFinished')
                break
 
        # step2A - Play Menu audio
        # kripaya yesh hospital ko sewa bare bhjhna 1 thichnuhos. yesh hospital sanga
        # sambandhit samashya Report garna 2 thichnuhos.
        self.subscribe_event('PlaybackFinished')
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'nuwakot/2'))
        requests.post(req_str, auth=(username, password))

        while True:
            time.sleep(0.3)
            if self.eventDict['PlaybackFinished']['status']:
                self.unsubscribe_event('PlaybackFinished')
                break

        # step2B - Wait for dtmf input for menu. Choices are 1 and 2
        self.subscribe_event('ChannelDtmfReceived')
        dtmf = ''
        #total_len = 3
        while True:
            time.sleep(0.3)
            if self.eventDict['ChannelDtmfReceived']['status']:
                digit = self.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                if digit == '1':
                    print dtmf
                    self.unsubscribe_event('ChannelDtmfReceived')
                    #step 2B.1
                    Menu1()
                    break
                elif digit == '2':
                    print dtmf
                    self.unsubscribe_event('ChannelDtmfReceived')
                    #step 2B.2
                    Menu2()


    def event(self, event_json):
        event_type = event_json['type']
        if event_type in self.eventDict:
            self.eventDict[event_type]['status'] = True
            self.eventDict[event_type]['eventJson'] = event_json

    def subscribe_event(self, eventName):
        if eventName not in self.eventDict:
            self.eventDict[eventName] = {}
            self.eventDict[eventName]['status'] = False
        else:
            print 'Duplicate entry!'

    def unsubscribe_event(self, eventName):
        if eventName in self.eventDict:
            self.eventDict.pop(eventName)
        else:
            print 'No event of this type!'

    def end(self, start_time, end_time):
        print 'End of VNuwakot'
        pass
        print '\n\nVSurvey output: ', self.output
        start_time = arrow.get(start_time)
        end_time = arrow.get(end_time)
        duration = (end_time - start_time).total_seconds()

        self.channels_inuse -= 1
        query = Services.update(channels_inuse = self.channels_inuse).where(Services.extension == self.exten)
        query.execute()
        print self.allocated_channels, self.channels_inuse

        IncomingLog.create(org_id = self.org_id, service = self.service_name, call_start_time = start_time.isoformat(), \
                           call_end_time = end_time.isoformat(), call_duration = duration, completecall = self.playbackCompleted, \
                           incoming_number = self.incoming_number, extension = self.exten)
        GeneralizedDataIncoming.create(data = self.output, incoming_number = self.incoming_number,\
                                       generalized_dialplan = self.module_id)


