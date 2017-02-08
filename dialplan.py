

import requests
import websocket
import json
import threading
import time
import uuid
from models import GeneralizedDialplan, Services

server_addr = 'localhost'
app_name = 'hello-world'
username = 'asterisk'
password = 'asterisk'
url = "ws://%s:8088/ari/events?app=%s&api_key=%s:%s" % (server_addr, app_name, username, password)

req_base = "http://%s:8088/ari/" % server_addr

ws = websocket.create_connection(url)

activeCalls = {}

class VBoard(threading.Thread):

    def __init__(self, channel_id, dialplan):
        super(VBoard, self).__init__()
        self.eventDict = {}
        self.channel_id = channel_id
        self.dialplan_json = dialplan

    def run(self):
        import ipdb;ipdb.set_trace();
        print self.dialplan_json
        tot = self.dialplan_json['nodeDataArray'][1]['options']['total-notices']
        welcome_audio = self.dialplan_json['nodeDataArray'][0]['options']['audiofile']
        notice_audios = [items['options']['audiofile'] for items in self.dialplan_json['nodeDataArray'][1:tot+1]]
        repeat_audio = self.dialplan_json['nodeDataArray'][-2]['options']['audiofile']

        req_str = req_base + "channels/%s/answer" % self.channel_id
        a = requests.post(req_str, auth=(username, password))
        if a.status_code == 204:
            print '\nCall Answer Time: ', time.ctime()

        # step1 - welcome message
        self.subscribe_event('PlaybackFinished')
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, welcome_audio))
        requests.post(req_str, auth=(username, password))

        while True:
            if self.eventDict['PlaybackFinished']['status']:
                self.unsubscribe_event('PlaybackFinished')
                break

        while True:
            # step2 - notice message
            # sound-lists
            # sounds = ['hello-world', 'hello-world', 'goodbye']
            for sound in notice_audios:
                self.subscribe_event('PlaybackFinished')
                req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, sound))
                requests.post(req_str, auth=(username, password))

                while True:
                    if self.eventDict['PlaybackFinished']['status']:
                        self.unsubscribe_event('PlaybackFinished')
                        break

            # step3 - repeat message
            self.subscribe_event('PlaybackFinished')
            req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, repeat_audio))
            requests.post(req_str, auth=(username, password))

            while True:
                if self.eventDict['PlaybackFinished']['status']:
                    self.unsubscribe_event('PlaybackFinished')
                    break

            # dtmf block
            self.subscribe_event('ChannelDtmfReceived')
            while True:
                if self.eventDict['ChannelDtmfReceived']['status']:
                    digit = self.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                    if digit == '*':
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
            print 'No event of this type!'

    def end(self):
        self.eventDict = {}


class VSurvey(threading.Thread):

    def __init__(self, channel_id, dialplan):
        super(VSurvey, self).__init__()
        self.eventDict = {}
        self.channel_id = channel_id

    def run(self):
        req_str = req_base + "channels/%s/answer" % self.channel_id
        a = requests.post(req_str, auth=(username, password))
        if a.status_code == 204:
            print '\nCall Answer Time: ', time.ctime()

        # step1 - welcome message
        self.subscribe_event('PlaybackFinished')
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'welcome'))
        requests.post(req_str, auth=(username, password))

        while True:
            if self.eventDict['PlaybackFinished']['status']:
                self.unsubscribe_event('PlaybackFinished')
                break

        # step2 - notice message
        self.subscribe_event('PlaybackFinished')
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'hello-world'))
        requests.post(req_str, auth=(username, password))

        while True:
            if self.eventDict['PlaybackFinished']['status']:
                self.unsubscribe_event('PlaybackFinished')
                break

        # step3 - record application
        self.subscribe_event('RecordingFinished')
        fname = uuid.uuid1()
        req_str = req_base+"channels/{0}/record?name={1}&format={2}&maxDurationSeconds={3}&ifExists={4}&beep={5}&terminateOn={6}"\
        .format(channel_id, fname, 'wav', 10, 'overwrite', True, 'any')
        requests.post(req_str, auth=(username, password))

        print '\n\n', self.eventDict
        self.subscribe_event('ChannelDtmfReceived')
        print '\n\n', self.eventDict
        while True:
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
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'options'))
        requests.post(req_str, auth=(username, password))

        while True:
            if self.eventDict['PlaybackFinished']['status']:
                self.unsubscribe_event('PlaybackFinished')
                break

        # dtmf block
        self.subscribe_event('ChannelDtmfReceived')
        while True:
            if self.eventDict['ChannelDtmfReceived']['status']:
                digit = self.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                if digit == '1':
                    print digit
                    self.unsubscribe_event('ChannelDtmfReceived')
                    break
                elif digit == '2':
                    print digit
                    self.unsubscribe_event('ChannelDtmfReceived')
                    break

        # step5 - thank you message
        self.subscribe_event('PlaybackFinished')
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'goodbye'))
        requests.post(req_str, auth=(username, password))

        while True:
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

    def end(self):
        pass
        # self.eventDict = {}

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

def get_dialplan_from_db(channel_id, exten):
    for service in Services.select().where(Services.extension == exten, Services.isactive == True):
        gen_dialplan = GeneralizedDialplan.select().where(GeneralizedDialplan.id == service.service.id)
        service_type = service.service_type.id
        dialplan = gen_dialplan[0].dialplan
        if service_type == 1:
            return VBoard(channel_id, dialplan)
        elif service_type == 2:
            return VSurvey(channel_id, dialplan)

try:
    for event_str in iter(lambda: ws.recv(), None):
        event_json = json.loads(event_str)
        event_type = event_json['type']

        if event_json['type'] == 'StasisStart':
            channel_id = event_json['channel']['id']
            exten = event_json['channel']['dialplan']['exten']
            print '\nStasis Start Time: ', channel_id, time.ctime()
            if channel_id not in activeCalls:
                # activeCalls[channel_id] = simulate(channel_id, exten)
                activeCalls[channel_id] = get_dialplan_from_db(channel_id, exten)
                activeCalls[channel_id].start()

        elif event_json['type'] =='StasisEnd':
            print 'StasisEnd'
            channel_id = event_json['channel']['id']
            print '\nStasis End Time: ', channel_id, time.ctime()
            if channel_id in activeCalls:
                activeCalls[channel_id].end()
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
