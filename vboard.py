
import threading
from nodes.answer import AnswerNode
from nodes.hangup import HangupNode
from nodes.audio import AudioNode
from nodes.dtmf import DtmfNode
from log import Log
from model import Service
from config import db


class VBoard(threading.Thread):
    def __init__(self, **kwargs):
        super(VBoard, self).__init__()
        self.eventDict = {}
        self.kwargs = kwargs
        self.uuids = []
        self.output = {
            'playbackCompleted' : False,
            'timesRepeated' : 0
        }


    def run(self):
        tot = self.kwargs['dialplan']['nodeDataArray'][1]['options']['total-notices']
        self.welcome_audio = self.kwargs['dialplan']['nodeDataArray'][0]['options']['audiofile']
        self.notice_audios = [items['options']['audiofile'] for items in self.kwargs['dialplan']['nodeDataArray'][1:tot + 1]]
        self.repeat_audio = [self.kwargs['dialplan']['nodeDataArray'][-2]['options']['audiofile']]

        if self.kwargs['channels_inuse'] < self.kwargs['allocated_channels']:
            answer = AnswerNode(**self.kwargs)
            answer_status = answer.answer()

            if answer_status.status_code == 204:
                self.kwargs['channels_inuse'] += 1
                query = Service.query.filter(Service.extension == self.kwargs['exten'])
                query[0].channels_inuse = self.kwargs['channels_inuse']
                db.session.commit()
        else:
            # hangup
            hangup = HangupNode(**self.kwargs)
            hangup.hang_up()

        # audio message
        audio = AudioNode(self, **self.kwargs)

        self.stat1 = audio.play_audio(blocking = True, audio = self.welcome_audio)
        self.stat2 = audio.play_audio(blocking = False, audio = self.notice_audios)
        self.stat3 = audio.play_audio(blocking = False, audio = self.repeat_audio)

        # dtmf handling
        dtmf = DtmfNode(self, options=['*', '#'])
        dtmf_digit = dtmf.get_dtmf()
        while dtmf_digit:
            audio.delete_audio(self.uuids)
            if dtmf_digit == '*':
                self.output['timesRepeated'] += 1
                self.stat2 = audio.play_audio(blocking=False, audio=self.notice_audios)
                self.stat3 = audio.play_audio(blocking=False, audio=self.repeat_audio)
                dtmf_digit = dtmf.get_dtmf()
                if dtmf_digit: continue
            elif dtmf_digit == '#':
                # hangup
                hangup = HangupNode(**self.kwargs)
                hangup.hang_up()


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
        if self.kwargs['channels_inuse'] > 0:
            self.kwargs['channels_inuse'] -= 1
            query = Service.query.filter(Service.extension == self.kwargs['exten'])
            query[0].channels_inuse = self.kwargs['channels_inuse']
            db.session.commit()
            if self.stat2:
                self.output['playbackCompleted'] = self.stat2['PlaybackFinished']
        else:
            print '\nNegative Count!!!!\n'
        # print start_time, end_time
        # print '\nOutput: ', self.output
        Log(self.output)
