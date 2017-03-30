
import threading
import arrow
from nodes.answer import AnswerNode
from nodes.hangup import HangupNode
from nodes.audio import AudioNode
from nodes.dtmf import DtmfNode
from nodes.record import RecordNode
from log import Log
from model import Service, GeneralizedDataIncoming, IncomingLog
from config import db
from utilities import utils


class VNuwakot(threading.Thread):
    def __init__(self, **kwargs):
        super(VNuwakot, self).__init__()
        self.eventDict = {}
        self.kwargs = kwargs
        self.uuids = []
        self.output = {
            'vboard': {
                'vboard1': False, 'vboard2': False
            },
            'vsurvey': {
                'status': False, 'vdc_audio': None, 'emergency_or_eye': None, 'msg_audio': None
            },
            'completed': False
        }
        self.fnames = []
        # set database row with default value (initialize row)
        self.generalized_data_incoming = GeneralizedDataIncoming(data=self.output, incoming_number=self.kwargs['incoming_number'], \
                                                            generalized_dialplan_id=self.kwargs['module_id'])
        db.session.add(self.generalized_data_incoming)
        db.session.commit()
        self.generalized_data_incoming_id = self.generalized_data_incoming.id
        self.il = IncomingLog(org_id=self.kwargs['org_id'], service=self.kwargs['service_name'], call_start_time='2017-03-24 16:34:23', \
                         call_end_time='2017-03-24 16:34:23', call_duration=0.0, complete=self.output['completed'], \
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


        def Menu1():
            self.stat2 = audio.play_audio(blocking = False, audio = ['nuwakot/3'])

            # wait for dtmf
            dtmf = DtmfNode(self, options=['*', '#'])
            dtmf_digit = dtmf.get_dtmf()
            while dtmf_digit:
                audio.delete_audio(self.uuids)
                if dtmf_digit == '1':
                    self.stat3 = audio.play_audio(blocking = True, audio = ['nuwakot/4'])
                    self.output['vboard']['vboard1'] = True
                    break
                elif dtmf_digit == '2':
                    self.stat4 = audio.play_audio(blocking = True, audio = ['nuwakot/5'])
                    self.output['vboard']['vboard2'] = True
                    break

            # log
            self.output['completed'] = True

            # hangup
            hangup = HangupNode(**self.kwargs)
            hangup.hang_up()


        def Menu2():
            #Tapiko ga bi sa wa nagarpalika ko naam bhannuhos ani # thichuhos
            self.stat5 = audio.play_audio(blocking = True, audio = ['nuwakot/6'])

            # record application
            record = RecordNode(self, **self.kwargs)
            fname = record.start_record()
            self.fnames.append(str(fname))

            # log
            self.output['vsurvey']['status'] = True
            self.output['vsurvey']['vdc_audio'] = str(fname)

            # kripaya emeergency sewa sambandhi samasya rakhna ko lagi 1 or akhako sewa sambandhi samasya rakhna ko lagi
            # 2 thichnuhos
            self.stat6 = audio.play_audio(blocking = False, audio = ['nuwakot/7'])

            # wait for dtmf
            dtmf = DtmfNode(self, options=['*', '#'])
            dtmf_digit = dtmf.get_dtmf()
            while dtmf_digit:
                audio.delete_audio(self.uuids)
                if dtmf_digit == '1':
                    self.output['vsurvey']['emergency_or_eye'] = dtmf_digit
                    break
                elif dtmf_digit == '2':
                    self.output['vsurvey']['emergency_or_eye'] = dtmf_digit
                    break

            # tapaiko samasya vannuhos ani # thichnuhos
            self.stat7 = audio.play_audio(blocking = True, audio = ['nuwakot/8'])

            # record application
            record = RecordNode(self, **self.kwargs)
            fname = record.start_record()
            self.fnames.append(str(fname))

            # log
            self.output['vsurvey']['msg_audio'] = str(fname)

            # tapaiko samasya record vaeko xa
            self.stat8 = audio.play_audio(blocking = True, audio = ['nuwakot/9'])

            # log
            self.output['completed'] = True

            # hangup
            hangup = HangupNode(**self.kwargs)
            hangup.hang_up()


        # audio message
        audio = AudioNode(self, **self.kwargs)

        # welcome audio
        # Namaskar Nuwakot Hospital ko IVR sewa ma yaha lai swagat cha
        self.stat1 = audio.play_audio(blocking = True, audio = ['nuwakot/1'])

        # step2A - Play Menu audio
        # kripaya yesh hospital ko sewa bare bhjhna 1 thichnuhos. yesh hospital sanga
        # sambandhit samashya Report garna 2 thichnuhos.
        self.stat2 = audio.play_audio(blocking = False, audio = ['nuwakot/2'])

        # step2B - Wait for dtmf input for menu. Choices are 1 and 2
        # dtmf handling
        dtmf = DtmfNode(self, options=['*', '#'])
        dtmf_digit = dtmf.get_dtmf()
        while dtmf_digit:
            audio.delete_audio(self.uuids)
            if dtmf_digit == '1':
                # step 2B.1
                Menu1()
                break
            elif dtmf_digit == '2':
                # step 2B.2
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
        self.il.complete = self.output['completed']
        self.il.generalized_dialplan_id = self.generalized_data_incoming_id
        db.session.commit()

        ############## moving recorded files ##############
        utils.move_files(self.fnames)
