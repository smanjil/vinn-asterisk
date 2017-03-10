
import requests
import websocket
import json
import uuid
import threading

server_addr = 'localhost'
app_name = 'hello-world'
username = 'asterisk'
password = 'asterisk'

url = "ws://%s:8088/ari/events?app=%s&api_key=%s:%s" % (server_addr, app_name, username, password)
req_base = "http://%s:8088/ari/" % server_addr

ws = websocket.create_connection(url)

activeCalls = {}


class VDialplanOperator(threading.Thread):
    def __init__(self, channel_id):
        super(VDialplanOperator, self).__init__()
        self.eventDict = {}
        self.channel_id = channel_id

    def run(self):
        print '\n-----Creating a holding bridge------\n'
        req_str = req_base + "bridges?type={0}" .format('holding')
        a = requests.post(req_str, auth=(username, password))
        print a.text

        bridge_json = json.loads(a.text)
        holding_bridge_id = bridge_json['id']
        print '\nHolding bridgeid: ', holding_bridge_id

        print '\nIncoming channel id: ', self.channel_id

        print '\n----Adding incoming channel to holding bridge----\n'
        req_str = req_base + "bridges/{0}/addChannel?channel={1}" .format(holding_bridge_id, self.channel_id)
        a = requests.post(req_str, auth=(username, password))
        print '\nStatus of adding incoming channel to holding bridge: ', a.status_code

        self.subscribe_event('StasisStart')

        print '\n-----------Originating the outgoing channel----------\n'
        req_str = req_base + "channels?endpoint={0}&app={1}&appArgs={2}" .format('SIP/3004', 'hello-world', self.channel_id)
        a = requests.post(req_str, auth=(username, password))
        bridge_channel_json = json.loads(a.text)
        outgoing_channel_id = bridge_channel_json['id']
        print '\nOutgoing channel id: ', outgoing_channel_id

        while True:
           if self.eventDict['StasisStart']['status']:
               self.unsubscribe_event('StasisStart')
               break

        print '\n-----------------Creating mixing bridge-----------\n'
        req_str = req_base + "bridges?type={0}" .format('mixing')
        a = requests.post(req_str, auth=(username, password))
        print a.text

        bridge_json = json.loads(a.text)
        mixing_bridge_id = bridge_json['id']
        print '\nMixing bridgeid: ', mixing_bridge_id

        print '\n-------Answering the outgoing channel---------\n'
        req_str = req_base + "channels/{0}/answer" .format(self.channel_id)
        a = requests.post(req_str, auth=(username, password))
        print '\nStatus of answering channel: ', a.status_code

        if a.status_code == 204:
            print '\n----Adding outgoing channel to mixing bridge----\n'
            req_str = req_base + "bridges/{0}/addChannel?channel={1}" .format(mixing_bridge_id, self.channel_id + ',' + outgoing_channel_id)
            a = requests.post(req_str, auth=(username, password))
            print '\nStatus of adding outgoing channel to mixing bridge: ', a.status_code

            print '\nStart live recording within the mixing bridge!------\n'
            req_str = req_base + "bridges/{0}/record?name={1}&format={2}&ifExists={3}" .format(mixing_bridge_id, 'bridge-record', 'wav', 'overwrite')
            requests.post(req_str, auth=(username, password))

        print '\n-----Listing available bridges------\n'
        req_str = req_base + "bridges"
        available_bridges = requests.get(req_str, auth=(username, password))
        print available_bridges.text

        print '\n----Deleting holding bridge---\n'
        req_str = req_base + "bridges/{0}" .format(holding_bridge_id)
        a = requests.delete(req_str, auth=(username, password))
        print '\nStatus of deleting holding brige: ', a.status_code

        self.subscribe_event('ChannelHangupRequest')
        while True:
            if self.eventDict['ChannelHangupRequest']['status']:
                bridge_list = json.loads(available_bridges.text)
                channels_list = [bridge['channels'] for bridge in bridge_list if bridge['bridge_type'] == 'mixing'][0]
                for channel in channels_list:
                    req_str = req_base + "channels/{0}" .format(channel)
                    requests.delete(req_str, auth=(username, password))
                req_str = req_base + "bridges/{0}" .format(mixing_bridge_id)
                a = requests.delete(req_str, auth=(username, password))
                print a.text
                self.unsubscribe_event('ChannelHangupRequest')
                break

        return


    def event(self, event_json):
        event_type = event_json['type']
        if event_type in self.eventDict:
           self.eventDict[event_type]['status'] = True
#           self.eventDict[event_type]['eventJson'] = event_json


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


    def end(self, channel_id):
        print 'The control is at end!!!!', channel_id


try:
    for event_str in iter(lambda: ws.recv(), None):
        event_json = json.loads(event_str)
        event_type = event_json['type']

        print event_type

        if event_json['type'] == 'StasisStart':
            print 'Stasis Start'
            channel_id = event_json['channel']['id']

            if event_json['args']:
                parent_channel_id = event_json['args'][0]
                print 'Parent : ', parent_channel_id
            else:
                parent_channel_id = channel_id

            if parent_channel_id not in activeCalls:
                print 'New call!', channel_id
                activeCalls[channel_id] = VDialplanOperator(channel_id)
                activeCalls[channel_id].start()
            else:
                print 'bridge call', channel_id, parent_channel_id
                activeCalls[channel_id] = activeCalls[parent_channel_id]
                activeCalls[channel_id].event(event_json)
        elif event_json['type'] == 'StasisEnd':
            print 'Stasis End'
            channel_id = event_json['channel']['id']
            print channel_id
            if channel_id in activeCalls:
                activeCalls[channel_id].end(channel_id)
        elif event_json['type'] == 'ChannelHangupRequest':
            channel_id = event_json['channel']['id']
            print channel_id
            print 'ActiveCalls: ', activeCalls
            activeCalls[channel_id].event(event_json)
            del activeCalls[channel_id]
except websocket.WebSocketConnectionClosedException:
    print 'Websocket Connection Closed'
except KeyboardInterrupt:
    print 'Keyboard Interrupt'
finally:
    if ws:
        ws.close()
