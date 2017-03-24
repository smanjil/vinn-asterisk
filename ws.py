
import sys
sys.path.append('/home/ano/voiceinn/voiceinn-asterisk/')

import websocket
import json
from vboard import VBoard
from vsurvey import VSurvey
from model import Service, GeneralizedDialplan

server_addr = 'localhost'
app_name = 'hello-world'
username = 'asterisk'
password = 'asterisk'
url = "ws://%s:8088/ari/events?app=%s&api_key=%s:%s" % (server_addr, app_name, username, password)

req_base = "http://%s:8088/ari/" % server_addr

ws = websocket.create_connection(url)

activeCalls = {}


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
        kwargs['req_base'] = req_base
        kwargs['username'] = username
        kwargs['password'] = password

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
                activeCalls[channel_id] = get_dialplan_from_db(channel_id, exten, incoming_number)
                activeCalls[channel_id].start()

        elif event_json['type'] =='StasisEnd':
            print 'StasisEnd'
            start_time = event_json['channel']['creationtime']
            end_time = event_json['timestamp']
            if channel_id in activeCalls:
                activeCalls[channel_id].end(start_time, end_time)
                del activeCalls[channel_id]

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
