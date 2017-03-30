
import threading
import arrow
import time
from nodes.answer import AnswerNode
from nodes.hangup import HangupNode
from nodes.audio import AudioNode
from nodes.dtmf import DtmfNode
from nodes.record import RecordNode
from log import Log
from model import Service, GeneralizedDataIncoming, IncomingLog
from config import db


class VDemo(threading.Thread):
    def __init__(self, **kwargs):
        super(VDemo, self).__init__()
        self.eventDict = {}
        self.kwargs = kwargs
        self.uuids = []
        self.output = {}

        # nodes initilization
        self.audio = AudioNode(self, **kwargs)
        self.dtmf = DtmfNode(self, options=['1', '2'])
        self.record = RecordNode(self, **self.kwargs)

        # set database row with default value (initialize row)
        # self.generalized_data_incoming = GeneralizedDataIncoming(data=self.output, incoming_number=self.kwargs['incoming_number'], \
        #                                                     generalized_dialplan_id=self.kwargs['module_id'])
        # db.session.add(self.generalized_data_incoming)
        # db.session.commit()
        # self.generalized_data_incoming_id = self.generalized_data_incoming.id
        # self.il = IncomingLog(org_id=self.kwargs['org_id'], service=self.kwargs['service_name'], call_start_time='2017-03-24 16:34:23', \
        #                  call_end_time='2017-03-24 16:34:23', call_duration=0.0, complete=self.output['playbackCompleted'], \
        #                  incoming_number=str(self.kwargs['incoming_number']), extension=str(self.kwargs['exten']), \
        #                  generalized_data_incoming=self.generalized_data_incoming_id, status='unsolved')
        # db.session.add(self.il)
        # db.session.commit()
    

    def repeater(self, audio):
        audio_name = audio

        # play repeater audio
        self.repeat = self.audio.play_audio(blocking = False, audio = audio_name)

        # wait for dtmf input
        dtmf_digit = self.dtmf.get_dtmf()
        while dtmf_digit:
            time.sleep(0.3)
            if dtmf_digit == '1':
                # repeat the description
                self.repeater(audio_name)
            elif dtmf_digit == '2':
                # demo
                return dtmf_digit
            elif dtmf_digit == '3':
                # go back to main menu
                self.menu()


    def vboard(self, audio):
        audio_name = audio
        
        # play dscription audio
        self.vboard_description = self.audio.play_audio(blocking = True, audio = audio_name)


        # vboard demo
        def vboard_demo():
            # beep
            self.beep = self.audio.play_audio(blocking = True, audio = 'beep.wav')

            # noticeboard description
            self.noticeboard_description = self.audio.play_audio(blocking = True, audio = 'noticeboard-desc-{0}.wav' .format(self.language))

            # repeater message
            self.demo_repeat = self.audio.play_audio(blocking = False, audio = 'repeater-english.{0}' .format(self.language))

            # wait for dtmf input
            dtmf_digit = self.dtmf.get_dtmf()
            while dtmf_digit:
                time.sleep(0.3)
                if dtmf_digit == '*':
                    # repeat the noticeboard description
                    vboard_demo()
                elif dtmf_digit == '#':
                    # go back to the main menu
                    self.menu()             

            # beep
            self.beep = self.audio.play_audio(blocking = True, audio = 'beep.wav')

            # repeater message
            digit = self.repeater(audio = 'vboard-repeater-{0}.wav' .format(self.language))

        if digit == '2':
            vboard_demo()
    

    def menu(self):
        # play menu audio
        self.menu = self.audio.play_audio(blocking = True, audio = 'menu-{0}.wav' .format(self.language))

        # wait for menu input to choose services
        dtmf_digit = self.dtmf.get_dtmf()
        while dtmf_digit:
            time.sleep(0.3)
            if dtmf_digit == '1':
                # vboard service selected
                self.vboard(audio = 'vboard-desc-{0}.wav' .format(self.language))
            elif dtmf_digit == '2':
                # vsurvey service selected
                pass
            elif dtmf_digit == '3':
                # vreport service selected
                pass
            elif dtmf_digit == '4':
                # vsupport service selected
                pass
            elif dtmf_digit == '5':
                # vbroadcast service selected
                pass
            elif dtmf_digit == '*':
                # chosen to repeat the menu
                pass
            elif dtmf_digit == '#':
                # chosen to hangup
                pass

    
    def nepali(self):
        self.language = 'nepali'

        # description of vboard in nepali
        self.voiceinn_desc = self.audio.play_audio(blocking = True, audio = 'voiceinn-desc-{0}.wav' .format(self.language))

        # play menu to choose various services related to voiceinn_desc
        self.menu()


    def english(self):
        self.language = 'english'

        # description of vboard in english
        self.voiceinn_desc = self.audio.play_audio(blocking = True, audio = 'voiceinn-desc-{0}.wav' .format(self.language))

        # play menu to choose various services related to voiceinn_desc
        self.menu()

    
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
        
        # welcome to voiceinn demo (demo1.wav)
        self.welcome = self.audio.play_audio(blocking = False, audio = 'welcome-demo1.wav')

        # language option choosing
        dtmf_digit = self.dtmf.get_dtmf()
        while dtmf_digit:
            time.sleep(0.3)
            if dtmf_digit == '1':
                # chosen nepali language option
                self.nepali()
            elif dtmf_digit == '2':
                # chosen english language option
                self.english()
    

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
        print 'End'
        # start_time = arrow.get(start_time)
        # end_time = arrow.get(end_time)
        # duration = (end_time - start_time).total_seconds()

        # if self.kwargs['channels_inuse'] > 0:
        #     self.kwargs['channels_inuse'] -= 1
        #     query = Service.query.filter(Service.extension == self.kwargs['exten'])
        #     query[0].channels_inuse = self.kwargs['channels_inuse']
        #     db.session.commit()
        #     try:
        #         if self.stat2:
        #             self.output['playbackCompleted'] = self.stat2['PlaybackFinished']
        #     except:
        #         print '\nException: "self.stat2" not defined!!!!\n'
        #         self.output['playbackCompleted'] = False
        # else:
        #     print '\nNegative Count!!!!\n'
        # print start_time, end_time
        # print '\nOutput: ', self.output
        # Log(self.output)

        # update records in database
        # self.generalized_data_incoming.data = self.output
        # db.session.commit()

        # self.il.call_start_time = start_time.isoformat()
        # self.il.call_end_time = end_time.isoformat()
        # self.il.call_duration = duration
        # self.il.complete = self.output['playbackCompleted']
        # self.il.generalized_dialplan_id = self.generalized_data_incoming_id
        # db.session.commit()
