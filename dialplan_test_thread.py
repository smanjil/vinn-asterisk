
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
    eventDict = {}

    def __init__(self, channel_id):
        super(Dialplan, self).__init__()
        self.channel_id = channel_id
        print self.channel_id

    def run(self):
        req_str = req_base + "channels/%s/answer" % self.channel_id
        requests.post(req_str, auth=(username, password))

        self.subscribe_event('PlaybackFinished')
        req_str = req_base + ("channels/%s/play?media=sound:%s" % (self.channel_id, 'hello-world'))
        requests.post(req_str, auth=(username, password))

        while True:
            if self.eventDict['PlaybackFinished']:
                self.unsubscribe_event('PlaybackFinished')
                break

        req_str = req_base + "channels/%s" % channel_id
        requests.delete(req_str, auth=(username, password))

    def event(self, event_json):
        event_type = event_json['type']
        print event_type
        if event_type in self.eventDict:
            self.eventDict[event_type] = True

    def subscribe_event(self, eventName):
        if eventName not in self.eventDict:
            self.eventDict[eventName] = False
        else:
            print 'Duplicate entry!'

    def unsubscribe_event(self, eventName):
        if eventName in self.eventDict:
            self.eventDict.pop(eventName)
        else:
            print 'No event of this type!'

    def end(self):
        pass


try:
    for event_str in iter(lambda: ws.recv(), None):
        event_json = json.loads(event_str)

        if event_json['type'] == 'StasisStart':
            channel_id = event_json['channel']['id']
            event_type = event_json['type']
            if channel_id not in activeCalls:
                activeCalls[channel_id] = Dialplan(channel_id)
                activeCalls[channel_id].start()

        elif event_json['type'] =='StasisEnd':
            if channel_id in activeCalls:
                activeCalls[channel_id].end()
                del activeCalls[channel_id]

        else:
            if channel_id in activeCalls:
                activeCalls[channel_id].event(event_json)

except websocket.WebSocketConnectionClosedException:
    print "Websocket connection closed"
except KeyboardInterrupt:
    print "Keyboard interrupt"
finally:
    if ws:
        ws.close()
