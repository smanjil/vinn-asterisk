
import requests
import websocket
import json
import threading

server_addr = 'localhost'
app_name = 'hello-world'
username = 'asterisk'
password = 'asterisk'
url = "ws://%s:8088/ari/events?app=%s&api_key=%s:%s" % (server_addr, app_name, username, password)

req_base = "http://%s:8088/ari/" % server_addr

ws = websocket.create_connection(url)

activeCalls = {}

class Dialplan(threading.Thread):

    def __init__(self, channel_id):
        super(Dialplan, self).__init__()
        self.eventDict = {}
        self.channel_id = channel_id

    def run(self):
        req_str = req_base + "channels/%s/answer" % self.channel_id
        requests.post(req_str, auth=(username, password))

        # step1 - welcome message
        self.subscribe_event('PlaybackFinished')
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'welcome'))
        requests.post(req_str, auth=(username, password))

        while True:
            if self.eventDict['PlaybackFinished']['status']:
                self.unsubscribe_event('PlaybackFinished')
                break

        while True:
            # step2 - notice message
            self.subscribe_event('PlaybackFinished')
            req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'hello-world'))
            requests.post(req_str, auth=(username, password))

            while True:
                if self.eventDict['PlaybackFinished']['status']:
                    self.unsubscribe_event('PlaybackFinished')
                    break

            # step3 - repeat message
            self.subscribe_event('PlaybackFinished')
            req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'repeater'))
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
                    print self.eventDict['ChannelDtmfReceived']['eventJson']['digit']
                    # self.unsubscribe_event('ChannelDtmfReceived')
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


try:
    for event_str in iter(lambda: ws.recv(), None):
        event_json = json.loads(event_str)
        event_type = event_json['type']

        if event_json['type'] == 'StasisStart':
            channel_id = event_json['channel']['id']
            if channel_id not in activeCalls:
                activeCalls[channel_id] = Dialplan(channel_id)
                activeCalls[channel_id].start()

        elif event_json['type'] =='StasisEnd':
            print 'StasisEnd'
            channel_id = event_json['channel']['id']
            if channel_id in activeCalls:
                activeCalls[channel_id].end()
                del activeCalls[channel_id]
                # activeCalls.pop(channel_id)

        else:
            if event_type=='PlaybackStarted':
                channel_id = event_json['playback']['target_uri'].split(':')[1]
            elif event_type=='PlaybackFinished':
                channel_id = event_json['playback']['target_uri'].split(':')[1]
            elif event_type=='ChannelDtmfReceived':
                channel_id = event_json['channel']['id']
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
