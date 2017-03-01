# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

import requests
import websocket
import threading
import time
import uuid
import arrow
from models import Services, GeneralizedDataIncoming, IncomingLog

server_addr = 'localhost'
app_name = 'hello-world'
username = 'asterisk'
password = 'asterisk'
req_base = "http://%s:8088/ari/" % server_addr


class VNuwakot(threading.Thread):
    def __init__(self, **kwargs):
        super(VNuwakot, self).__init__()
        self.eventDict = {}
        self.channel_id = kwargs['channel_id']
        self.incoming_number = kwargs['incoming_number']
        self.module_id = kwargs['module_id']
        self.service_name = kwargs['service_name']
        self.org_id = kwargs['org_id']
        self.exten = kwargs['exten']
        self.allocated_channels = kwargs['allocated_channels']
        self.channels_inuse = kwargs['channels_inuse']
        self.output = {}
        self.playbackCompleted = False
        self.fname = ''
        self.jsonoutput = {'vboard': {
                                      'vboard1':False,'vboard2':False},
                           'vsurvey': {
                                      'status':False,'vdc_audio':None,'emergency_or_eye':None,'msg_audio':None}}

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
            #self.subscribe_event('PlaybackFinished')
            id = uuid.uuid1()
            req_str = req_base + ("channels/%s/play/%s?media=sound:%s" % (self.channel_id, id, 'nuwakot/3'))
            requests.post(req_str, auth=(username, password))

            #while True:
            #    time.sleep(0.3)
            #    if self.eventDict['PlaybackFinished']['status']:
            #        self.unsubscribe_event('PlaybackFinished')
            #        break

            # step2B - Wait for dtmf input for menu. Choices are 1 and 2
            self.subscribe_event('ChannelDtmfReceived')
            digit = ''
            # total_len = 3
            while True:
                time.sleep(0.3)
                if self.eventDict['ChannelDtmfReceived']['status']:
                    digit = self.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                    if digit == '1':
                        print digit
                        self.unsubscribe_event('ChannelDtmfReceived')
                        req_str = req_base + ("playbacks/%s" % (id))
                        requests.delete(req_str, auth=(username, password))
                        # step 2B.1
                        self.subscribe_event('PlaybackFinished')
                        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'nuwakot/4'))
                        requests.post(req_str, auth=(username, password))

                        while True:
                            time.sleep(0.3)
                            if self.eventDict['PlaybackFinished']['status']:
                                self.unsubscribe_event('PlaybackFinished')
                                #log
                                self.jsonoutput['vboard']['vboard1'] = True
                                break
                        break
                    elif digit == '2':
                        print digit
                        self.unsubscribe_event('ChannelDtmfReceived')
                        req_str = req_base + ("playbacks/%s" % (id))
                        requests.delete(req_str, auth=(username, password))
                        d = uuid.uuid1()
                        # step 2B.2
                        self.subscribe_event('PlaybackFinished')
                        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'nuwakot/5'))
                        requests.post(req_str, auth=(username, password))

                        while True:
                            time.sleep(0.3)
                            if self.eventDict['PlaybackFinished']['status']:
                                self.unsubscribe_event('PlaybackFinished')
                                #log
                                self.jsonoutput['vboard']['vboard2'] = True
                                break
                        break
            # hangup
            req_str = req_base + "channels/%s" % self.channel_id
            requests.delete(req_str, auth=(username, password))
        #step 6
        def Menu2():
            #Tapiko ga bi sa wa nagarpalika ko naam bhannuhos ani # thichuhos
            self.subscribe_event('PlaybackFinished')
            req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'nuwakot/6'))
            requests.post(req_str, auth=(username, password))

            while True:
                time.sleep(0.3)
                if self.eventDict['PlaybackFinished']['status']:
                    self.unsubscribe_event('PlaybackFinished')
                    break

            self.subscribe_event('RecordingFinished')
            fname = uuid.uuid1()
            req_str = req_base + "channels/{0}/record?name={1}&format={2}&maxDurationSeconds={3}&ifExists={4}&beep={5}&terminateOn={6}" \
                .format(self.channel_id, fname, 'wav', 10, 'overwrite', True, 'any')
            requests.post(req_str, auth=(username, password))
            #log
            self.jsonoutput['vsurvey']['status'] = True
            self.jsonoutput['vsurvey']['vdc_audio'] = str(fname)

            self.output['recordedFileName'] = str(fname)

            self.subscribe_event('ChannelDtmfReceived')
            while True:
                time.sleep(0.3)
                if self.eventDict['ChannelDtmfReceived']['status']:
                    digit = self.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                    print digit
                    if digit == '#':
                        req_str = req_base + "recordings/live/{0}/stop".format(fname)
                        a = requests.post(req_str, auth=(username, password))
                        self.unsubscribe_event('ChannelDtmfReceived')
                        self.unsubscribe_event('RecordingFinished')
                        break
                if self.eventDict['RecordingFinished']['status']:
                    self.unsubscribe_event('ChannelDtmfReceived')
                    self.unsubscribe_event('RecordingFinished')
                    break

            # kripaya emeergency sewa sambandhi samasya rakhna ko lagi 1 or akhako sewa sambandhi samasya rakhna ko lagi
            # 2 thichnuhos
            #self.subscribe_event('PlaybackFinished')
            id = uuid.uuid1()
            req_str = req_base + ("channels/%s/play/%s?media=sound:%s" % (self.channel_id, id, 'nuwakot/7'))
            requests.post(req_str, auth=(username, password))

            #while True:
            #    time.sleep(0.3)
            #    if self.eventDict['PlaybackFinished']['status']:
            #        self.unsubscribe_event('PlaybackFinished')
            #        break

            self.subscribe_event('ChannelDtmfReceived')
            digit = ''
            # total_len = 3
            while True:
                time.sleep(0.3)
                if self.eventDict['ChannelDtmfReceived']['status']:
                    digit = self.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                    print digit
                    if int(digit) in range(1, 3):
                        req_str = req_base + ("playbacks/%s" % (id))
                        requests.delete(req_str, auth=(username, password))
                        self.unsubscribe_event('ChannelDtmfReceived')
                        #log
                        self.jsonoutput['vsurvey']['emergency_or_eye'] = digit
                        break

            # tapaiko samasya vannuhos ani # thichnuhos
            self.subscribe_event('PlaybackFinished')
            req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'nuwakot/8'))
            requests.post(req_str, auth=(username, password))

            while True:
                time.sleep(0.3)
                if self.eventDict['PlaybackFinished']['status']:
                    self.unsubscribe_event('PlaybackFinished')
                    break

            self.subscribe_event('RecordingFinished')
            fname = uuid.uuid1()
            req_str = req_base + "channels/{0}/record?name={1}&format={2}&maxDurationSeconds={3}&ifExists={4}&beep={5}&terminateOn={6}" \
                .format(self.channel_id, fname, 'wav', 10, 'overwrite', True, 'any')
            requests.post(req_str, auth=(username, password))
            #log
            self.jsonoutput['vsurvey']['msg_audio'] = str(fname)

            self.output['recordedFileName'] = str(fname)

            self.subscribe_event('ChannelDtmfReceived')
            while True:
                time.sleep(0.3)
                if self.eventDict['ChannelDtmfReceived']['status']:
                    digit = self.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                    if digit == '#':
                        print digit
                        req_str = req_base + "recordings/live/{0}/stop".format(fname)
                        a = requests.post(req_str, auth=(username, password))
                        self.unsubscribe_event('ChannelDtmfReceived')
                        self.unsubscribe_event('RecordingFinished')
                        break
                if self.eventDict['RecordingFinished']['status']:
                    self.unsubscribe_event('ChannelDtmfReceived')
                    self.unsubscribe_event('RecordingFinished')
                    break

            # tapaiko samasya record vaeko xa
            self.subscribe_event('PlaybackFinished')
            req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'nuwakot/9'))
            requests.post(req_str, auth=(username, password))

            while True:
                time.sleep(0.3)
                if self.eventDict['PlaybackFinished']['status']:
                    self.unsubscribe_event('PlaybackFinished')
                    break
            # hangup
            req_str = req_base + "channels/%s" % self.channel_id
            requests.delete(req_str, auth=(username, password))


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
        #self.subscribe_event('PlaybackFinished')
        id = uuid.uuid1()
        req_str = req_base + ("channels/%s/play/%s?media=sound:%s" % (self.channel_id, id, 'nuwakot/2'))
        requests.post(req_str, auth=(username, password))

        #while True:
        #    time.sleep(0.3)
        #    if self.eventDict['PlaybackFinished']['status']:
        #        self.unsubscribe_event('PlaybackFinished')
        #        break

        # step2B - Wait for dtmf input for menu. Choices are 1 and 2
        self.subscribe_event('ChannelDtmfReceived')
        digit = ''
        #total_len = 3
        while True:
            time.sleep(0.3)
            if self.eventDict['ChannelDtmfReceived']['status']:
                digit = self.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                if digit == '1':
                    print digit
                    self.unsubscribe_event('ChannelDtmfReceived')
                    req_str = req_base + ("playbacks/%s" % (id))
                    requests.delete(req_str, auth=(username, password))
                    #step 2B.1
                    Menu1()
                    break
                elif digit == '2':
                    print digit
                    self.unsubscribe_event('ChannelDtmfReceived')
                    req_str = req_base + ("playbacks/%s" % (id))
                    requests.delete(req_str, auth=(username, password))
                    #step 2B.2
                    Menu2()
                    break


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
        print self.jsonoutput
        print '\n\nVSurvey output: ', self.output
        start_time = arrow.get(start_time)
        end_time = arrow.get(end_time)
        duration = (end_time - start_time).total_seconds()

        self.channels_inuse -= 1
        query = Services.update(channels_inuse = self.channels_inuse).where(Services.extension == self.exten)
        query.execute()
        print self.allocated_channels, self.channels_inuse

        generalized_data_incoming = GeneralizedDataIncoming.create(data = self.jsonoutput, incoming_number = self.incoming_number,\
                                       generalized_dialplan = self.module_id)
        generalized_data_incoming_id = generalized_data_incoming.id
        IncomingLog.create(org_id = self.org_id, service = self.service_name, call_start_time = start_time.isoformat(), \
                           call_end_time = end_time.isoformat(), call_duration = duration, completecall = self.playbackCompleted, \
                           incoming_number = self.incoming_number, extension = self.exten, generalized_data_incoming = generalized_data_incoming_id)
