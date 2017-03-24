
import threading
from nodes.answer import AnswerNode
from nodes.hangup import HangupNode
from nodes.audio import AudioNode
from nodes.record import RecordNode
from nodes.dtmf import DtmfNode
from log import Log
from model import Service
from config import db
import os


class VSurvey(threading.Thread):
    def __init__(self, **kwargs):
        super(VSurvey, self).__init__()
        self.eventDict = {}
        self.kwargs = kwargs
        self.uuids = []
        self.output = {
            'surveyCompleted' : False,
            'recordedFileName1': '',
            'dtmf' : ''
        }


    def run(self):
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

        # welcome message
        self.stat1 = audio.play_audio(blocking = True, audio = '2002_vs_010_welcome')

        # question1
        self.stat2 = audio.play_audio(blocking = True, audio = '2002_vs_020_question1')

        # record application
        record = RecordNode(self, **self.kwargs)
        fname = record.start_record()
        self.output['recordedFileName1'] = fname

        # question2
        self.stat3 = audio.play_audio(blocking = False, audio = ['2002_vs_030_question2'])

        # dtmf handling for question 2 response
        dtmf = DtmfNode(self, options = ['*', '#'])
        dtmf_digit = dtmf.get_dtmf()
        # dtmf_digit = dtmf.get_multiple_dtmf(length = 5)
        self.output['dtmf'] = dtmf_digit

        print 'Done!'


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
            if self.output['dtmf']:
                self.output['surveyCompleted'] = True
        else:
            print '\nNegative Count!!!!\n'
        # print start_time, end_time
        # print '\nOutput: ', self.output
        Log(self.output)

        ######## moving recorded files #################
        source_files = '/var/spool/asterisk/recording/'
        destination_files = '/home/ano/voiceinn/voiceinn-web/static/'

        files = os.listdir(source_files)
        for f in files:
            src_fullpath = source_files + "/" + f
            dest_fullpath = destination_files + "/" + f
            os.system("mv " + src_fullpath + " " + dest_fullpath)
