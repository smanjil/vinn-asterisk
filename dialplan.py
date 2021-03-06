
from config import db
import requests
import websocket
import json
import threading
import time
import uuid
import arrow
import os
from model import GeneralizedDialplan, Service, GeneralizedDataIncoming, IncomingLog
from nuwakot import VNuwakot
from websocket_connection import server_addr, app_name, username, password, req_base, ws

activeCalls = {}

class VBoard(threading.Thread):

    def __init__(self, **kwargs):
        super(VBoard, self).__init__()
        self.eventDict = {}
        self.channel_id = kwargs['channel_id']
        self.dialplan_json = kwargs['dialplan']
        self.incoming_number = kwargs['incoming_number']
        self.module_id = kwargs['module_id']
        self.exten = kwargs['exten']
        self.service_name = kwargs['service_name']
        self.org_id = kwargs['org_id']
        self.allocated_channels = kwargs['allocated_channels']
        self.channels_inuse = kwargs['channels_inuse']
        self.output = {}
        self.playbackCompleted = False
        self.timesRepeated = 0

    def run(self):
        tot = self.dialplan_json['nodeDataArray'][1]['options']['total-notices']
        welcome_audio = self.dialplan_json['nodeDataArray'][0]['options']['audiofile']
        notice_audios = [items['options']['audiofile'] for items in self.dialplan_json['nodeDataArray'][1:tot+1]]
        repeat_audio = self.dialplan_json['nodeDataArray'][-2]['options']['audiofile']

        if self.channels_inuse < self.allocated_channels:
            req_str = req_base + "channels/%s/answer" % self.channel_id
            a = requests.post(req_str, auth=(username, password))
            if a.status_code == 204:
                self.channels_inuse += 1
                query = Service.query.filter(Service.extension == self.exten)
                query[0].channels_inuse = self.channels_inuse
                db.session.commit()
                print self.allocated_channels, self.channels_inuse
        else:
            # hang up
            req_str = req_base + "channels/%s" % channel_id
            requests.delete(req_str, auth=(username, password))

        self.output['playbackCompleted'] = self.playbackCompleted
        self.output['timesRepeated'] = self.timesRepeated

        # step1 - welcome message
        self.subscribe_event('PlaybackFinished')
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, welcome_audio))
        requests.post(req_str, auth=(username, password))

        while True:
            time.sleep(0.3)
            if self.eventDict['PlaybackFinished']['status']:
                self.unsubscribe_event('PlaybackFinished')
                break

        uuids_list = []
        while True:
            time.sleep(0.3)
            # step2 - notice message
            # sound-lists
            # sounds = ['hello-world', 'hello-world', 'goodbye']
            for sound in notice_audios:
                # self.subscribe_event('PlaybackFinished')
                id = uuid.uuid1()
                uuids_list.append(id)
                req_str = req_base + ("channels/%s/play/%s?media=sound:%s" % (self.channel_id, id, sound))
                requests.post(req_str, auth=(username, password))

                # while True:
                #     time.sleep(0.3)
                #     if self.eventDict['PlaybackFinished']['status']:
                #         self.unsubscribe_event('PlaybackFinished')
                #         break

            # step3 - repeat message
            # self.subscribe_event('PlaybackFinished')
            id = uuid.uuid1()
            uuids_list.append(id)
            req_str = req_base + ("channels/%s/play/%s?media=sound:%s" % (self.channel_id, id, repeat_audio))
            requests.post(req_str, auth=(username, password))

            # while True:
            #     time.sleep(0.3)
                # if self.eventDict['PlaybackFinished']['status']:
                #     self.unsubscribe_event('PlaybackFinished')
                    # self.playbackCompleted = True
                    # self.output['playbackCompleted'] = self.playbackCompleted
                    # self.output['timesRepeated'] = self.timesRepeated
                    # break

            self.playbackCompleted = True
            self.output['playbackCompleted'] = self.playbackCompleted

            # dtmf block
            self.subscribe_event('ChannelDtmfReceived')
            while True:
                time.sleep(0.3)
                if self.eventDict['ChannelDtmfReceived']['status']:
                    digit = self.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                    for ids in uuids_list:
                        req_str = req_base + ("playbacks/%s" % (ids))
                        requests.delete(req_str, auth=(username, password))
                    if digit == '*':
                        self.timesRepeated += 1
                        self.output['timesRepeated'] = self.timesRepeated
                        self.unsubscribe_event('ChannelDtmfReceived')
                        break
                    elif digit == '#':
                        self.unsubscribe_event('ChannelDtmfReceived')
                        break
            if digit == '#': break

        # hang up
        req_str = req_base + "channels/%s" % channel_id
        requests.delete(req_str, auth=(username, password))

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
            print 'No event of this type!', eventName

    def end(self, start_time, end_time):
        print '\nVBoard output: ', self.output, '\n'
        start_time = arrow.get(start_time)
        end_time = arrow.get(end_time)
        duration = (end_time - start_time).total_seconds()

        self.channels_inuse -= 1
        query = Service.query.filter(Service.extension == self.exten)
        query[0].channels_inuse = self.channels_inuse
        print self.allocated_channels, self.channels_inuse
        generalized_data_incoming = GeneralizedDataIncoming(data = self.output, incoming_number = self.incoming_number,\
                                           generalized_dialplan_id = self.module_id)
        db.session.add(generalized_data_incoming)
        db.session.commit()
        generalized_data_incoming_id = generalized_data_incoming.id
        il = IncomingLog(org_id = self.org_id, service = self.service_name, call_start_time = start_time.isoformat(), \
                           call_end_time = end_time.isoformat(), call_duration = duration, complete = self.playbackCompleted, \
                           incoming_number = str(self.incoming_number), extension = str(self.exten), \
                           generalized_data_incoming = generalized_data_incoming_id, status='unsolved')
        db.session.add(il)
        db.session.commit()


class VSurvey(threading.Thread):

    def __init__(self, **kwargs):
        super(VSurvey, self).__init__()
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

    def run(self):
        if self.channels_inuse < self.allocated_channels:
            req_str = req_base + "channels/%s/answer" % self.channel_id
            a = requests.post(req_str, auth=(username, password))
            if a.status_code == 204:
                self.channels_inuse += 1
                query = Service.query.filter(Service.extension == self.exten)
                query[0].channels_inuse = self.channels_inuse
                print self.allocated_channels, self.channels_inuse
        else:
            # hang up
            req_str = req_base + "channels/%s" % channel_id
            requests.delete(req_str, auth=(username, password))

        self.output['playbackCompleted'] = self.playbackCompleted
        self.output['recordedFileName'] = self.fname

        # step1 - welcome message
        self.subscribe_event('PlaybackFinished')
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, '2002_vs_010_welcome'))
        requests.post(req_str, auth=(username, password))

        while True:
            time.sleep(0.3)
            if self.eventDict['PlaybackFinished']['status']:
                self.unsubscribe_event('PlaybackFinished')
                break

        # step2 - notice message
        self.subscribe_event('PlaybackFinished')
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, '2002_vs_020_question1'))
        requests.post(req_str, auth=(username, password))

        while True:
            time.sleep(0.3)
            if self.eventDict['PlaybackFinished']['status']:
                self.unsubscribe_event('PlaybackFinished')
                break

        # step3 - record application
        self.subscribe_event('RecordingFinished')
        fname = uuid.uuid1()
        req_str = req_base+"channels/{0}/record?name={1}&format={2}&maxDurationSeconds={3}&ifExists={4}&beep={5}&terminateOn={6}"\
        .format(channel_id, fname, 'wav', 10, 'overwrite', True, 'any')
        requests.post(req_str, auth=(username, password))

        self.output['recordedFileName'] = str(fname)

        self.subscribe_event('ChannelDtmfReceived')
        while True:
            time.sleep(0.3)
            if self.eventDict['ChannelDtmfReceived']['status']:
                digit = self.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                if digit == '#':
                    req_str = req_base + "recordings/live/{0}/stop" .format(fname)
                    a = requests.post(req_str, auth=(username, password))
                    self.unsubscribe_event('ChannelDtmfReceived')
                    self.unsubscribe_event('RecordingFinished')
                    break
            if self.eventDict['RecordingFinished']['status']:
                self.unsubscribe_event('ChannelDtmfReceived')
                self.unsubscribe_event('RecordingFinished')
                break

        # step4 - repeat message
        self.subscribe_event('PlaybackFinished')
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, '2002_vs_030_question2'))
        requests.post(req_str, auth=(username, password))

        while True:
            time.sleep(0.3)
            if self.eventDict['PlaybackFinished']['status']:
                self.unsubscribe_event('PlaybackFinished')
                break

        # dtmf block
        self.subscribe_event('ChannelDtmfReceived')
        dtmf = ''
        total_len = 3
        while True:
            time.sleep(0.3)
            if self.eventDict['ChannelDtmfReceived']['status']:
                digit = self.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                if digit == '#':
                    print dtmf
                    self.unsubscribe_event('ChannelDtmfReceived')
                    break
                elif len(dtmf) == total_len:
                    print dtmf
                    self.unsubscribe_event('ChannelDtmfReceived')
                    break
                else:
                    dtmf += digit
                    self.eventDict['ChannelDtmfReceived']['status'] = False
                # if int(digit) in range(0, 10):
                #     print digit
                #     self.unsubscribe_event('ChannelDtmfReceived')
                #     break

        self.playbackCompleted = True
        self.output['playbackCompleted'] = self.playbackCompleted

        # step5 - thank you message
        self.subscribe_event('PlaybackFinished')
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, '2002_vs_040_endmsg'))
        requests.post(req_str, auth=(username, password))

        while True:
            time.sleep(0.3)
            if self.eventDict['PlaybackFinished']['status']:
                self.unsubscribe_event('PlaybackFinished')
                break

        # hang up
        req_str = req_base + "channels/%s" % channel_id
        requests.delete(req_str, auth=(username, password))

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
        print '\n\nVSurvey output: ', self.output
        start_time = arrow.get(start_time)
        end_time = arrow.get(end_time)
        duration = (end_time - start_time).total_seconds()

        self.channels_inuse -= 1
        query = Service.query.filter(Service.extension == self.exten)
        query[0].channels_inuse = self.channels_inuse
        print self.allocated_channels, self.channels_inuse
        generalized_data_incoming = GeneralizedDataIncoming(data = self.output, incoming_number = self.incoming_number,\
                                           generalized_dialplan_id = self.module_id)
        db.session.add(generalized_data_incoming)
        db.session.commit()
        generalized_data_incoming_id = generalized_data_incoming.id
        il = IncomingLog(org_id = self.org_id, service = self.service_name, call_start_time = start_time.isoformat(), \
                           call_end_time = end_time.isoformat(), call_duration = duration, complete = self.playbackCompleted, \
                           incoming_number = str(self.incoming_number), extension = str(self.exten), \
                           generalized_data_incoming = generalized_data_incoming_id, status='unsolved')
        db.session.add(il)
        db.session.commit()

        ######## moving recorded files #################
        source_files = '/var/spool/asterisk/recording/'
        destination_files = '/home/ano/voiceinn/voiceinn-web/static/'

        files = os.listdir(source_files)
        for f in files:
            src_fullpath = source_files + "/" + f
            dest_fullpath = destination_files + "/" + f
            os.system("mv " + src_fullpath + " " + dest_fullpath)

# def simulate(channel_id, exten):
#     if exten == '1001':
#         json1001 = {
#                 "nodeDataArray": [
#                       { "id": 1, "type": "Audio", "options": {"audiofile": "welcome"} },
#                       { "id": 2, "type": "Audio", "options": {"audiofile": "hello-world", "total-notices": 1} },
#                       { "id": 3, "type": "DTMFjump", "options": {"audiofile": "repeater"} },
#                       { "id": 4, "type": "Hangup", "options": {} },
#                     ],
#                 "linkDataArray": [
#                       { "from": 1, "to": 2},
#                       { "from": 2, "to": 3},
#                       { "from": 3, "to": 4},
#                 ]
#         }
#         return VBoard(channel_id, json1001)
#     elif exten == '1002':
#         json1002 = {
#                 "nodeDataArray": [
#                       { "id": 1, "type": "Audio", "options": {"audiofile": "welcome"} },
#                       { "id": 2, "type": "Audio", "options": {"audiofile": "hello-world", "total-notices": 2} },
#                       { "id": 3, "type": "Audio", "options": {"audiofile": "hello-world"} },
#                       { "id": 2, "type": "DTMFjump", "options": {"audiofile": "repeater"} },
#                       { "id": 4, "type": "Hangup", "options": {} },
#                     ],
#                 "linkDataArray": [
#                       { "from": 1, "to": 2},
#                       { "from": 2, "to": 3},
#                       { "from": 3, "to": 4},
#                 ]
#         }
#         return VBoard(channel_id, json1002)
#     elif exten == '2001':
#         json2001 = {
#                 "nodeDataArray": [
#                       { "id": 1, "type": "Audio", "options": {"audiofile": "welcome"} },
#                       { "id": 2, "type": "Audio", "options": {"audiofile": "hello-world", "total-notices": 3} },
#                       { "id": 3, "type": "Audio", "options": {"audiofile": "hello-world"} },
#                       { "id": 3, "type": "Audio", "options": {"audiofile": "hello-world"} },
#                       { "id": 2, "type": "DTMFjump", "options": {"audiofile": "repeater"} },
#                       { "id": 4, "type": "Hangup", "options": {} },
#                     ],
#                 "linkDataArray": [
#                       { "from": 1, "to": 2},
#                       { "from": 2, "to": 3},
#                       { "from": 3, "to": 4},
#                 ]
#         }
#         return VBoard(channel_id, json2001)
#     elif exten == '2002':
#         return VSurvey(channel_id)

def get_dialplan_from_db(channel_id, exten, incoming_number):
    kwargs = {}
    for service in Service.query.filter(Service.extension == str(exten) and Service.isActive == True):
        gen_dialplan = GeneralizedDialplan.query.filter(GeneralizedDialplan.id == service.service_id)
        service_type = service.service_types.id
        kwargs['channel_id'] = channel_id
        kwargs['dialplan'] = gen_dialplan[0].dialplan
        kwargs['incoming_number'] = incoming_number
        kwargs['module_id'] = service.service_id
        kwargs['exten'] = exten
        kwargs['service_name'] = service.service_types.name
        kwargs['org_id'] = service.org_id
        kwargs['allocated_channels'] = service.allocated_channels
        kwargs['channels_inuse'] = service.channels_inuse

        if service_type == 1:
            return VBoard(**kwargs)
        elif service_type == 2:
            return VSurvey(**kwargs)
        elif service_type == 3:
            return VNuwakot(**kwargs)

try:
    for event_str in iter(lambda: ws.recv(), None):
        event_json = json.loads(event_str)
        event_type = event_json['type']

        if event_json['type'] == 'StasisStart':
            channel_id = event_json['channel']['id']
            if event_json['args']:
                print event_json['args']
                exten = event_json['args'][0].split()[1]
                call_direction = 'outgoing'
                incoming_number = 'out ' + event_json['args'][0].split()[2]
            else:
                exten = event_json['channel']['dialplan']['exten']
                incoming_number = event_json['channel']['caller']['number']
                call_direction = 'incoming'

            if channel_id not in activeCalls:
                # activeCalls[channel_id] = simulate(channel_id, exten)
                activeCalls[channel_id] = get_dialplan_from_db(channel_id, exten, incoming_number)
                activeCalls[channel_id].start()

        elif event_json['type'] =='StasisEnd':
            print 'StasisEnd'
            start_time = event_json['channel']['creationtime']
            end_time = event_json['timestamp']
            if channel_id in activeCalls:
                activeCalls[channel_id].end(start_time, end_time)
                del activeCalls[channel_id]
                # activeCalls.pop(channel_id)

        else:
            if event_type == 'PlaybackStarted':
                channel_id = event_json['playback']['target_uri'].split(':')[1]
            elif event_type == 'PlaybackFinished':
                channel_id = event_json['playback']['target_uri'].split(':')[1]
            elif event_type == 'RecordingStarted':
                channel_id = event_json['recording']['target_uri'].split(':')[1]
            elif event_type == 'RecordingFinished':
                channel_id = event_json['recording']['target_uri'].split(':')[1]
            elif event_type == 'ChannelDtmfReceived':
                channel_id = event_json['channel']['id']
            elif event_type == 'ChannelHangupRequest':
                print '\nHangup Time: ', event_json['timestamp']
            else:
                print "Unknown channel_id for event ", event_type
                continue
            if channel_id in activeCalls:
                activeCalls[channel_id].event(event_json)

except websocket.WebSocketConnectionClosedException:
    print "Websocket connection closed"
except KeyboardInterrupt:
    print "Keyboard interrupt"
finally:
    if ws:
        ws.close()
