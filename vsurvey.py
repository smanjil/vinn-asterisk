
import threading
import arrow
from nodes.answer import AnswerNode
from nodes.hangup import HangupNode
from nodes.audio import AudioNode
from nodes.record import RecordNode
from nodes.dtmf import DtmfNode
from log import Log
from model import Service, GeneralizedDataIncoming, IncomingLog
from config import db
from utilities import utils


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
        self.fnames = []
        # set database row with default value (initialize row)
        self.generalized_data_incoming = GeneralizedDataIncoming(data=self.output, incoming_number=self.kwargs['incoming_number'], \
                                                            generalized_dialplan_id=self.kwargs['module_id'])
        db.session.add(self.generalized_data_incoming)
        db.session.commit()
        self.generalized_data_incoming_id = self.generalized_data_incoming.id
        self.il = IncomingLog(org_id=self.kwargs['org_id'], service=self.kwargs['service_name'], call_start_time='2017-03-24 16:34:23', \
                         call_end_time='2017-03-24 16:34:23', call_duration=0.0, complete=self.output['surveyCompleted'], \
                         incoming_number=str(self.kwargs['incoming_number']), extension=str(self.kwargs['exten']), \
                         generalized_data_incoming=self.generalized_data_incoming_id, status='unsolved')
        db.session.add(self.il)
        db.session.commit()


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
        self.fnames.append(str(fname))
        self.output['recordedFileName1'] = str(fname)

        # question2
        self.stat3 = audio.play_audio(blocking = False, audio = ['2002_vs_030_question2'])

        # dtmf handling for question 2 response
        dtmf = DtmfNode(self, options = ['*', '#'])
        dtmf_digit = dtmf.get_dtmf()
        # dtmf_digit = dtmf.get_multiple_dtmf(length = 5)
        self.output['dtmf'] = dtmf_digit

        # thank you message
        audio.play_audio(blocking = True, audio = '2002_vs_040_endmsg')

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
        start_time = arrow.get(start_time)
        end_time = arrow.get(end_time)
        duration = (end_time - start_time).total_seconds()

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

        # update records in database
        self.generalized_data_incoming.data = self.output
        db.session.commit()

        self.il.call_start_time = start_time.isoformat()
        self.il.call_end_time = end_time.isoformat()
        self.il.call_duration = duration
        self.il.complete = self.output['surveyCompleted']
        self.il.generalized_dialplan_id = self.generalized_data_incoming_id
        db.session.commit()

        ######## moving recorded files #################
        utils.move_files(self.fnames)
