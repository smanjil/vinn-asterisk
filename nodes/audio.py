
import requests
import time
import uuid


class AudioNode(object):
    def __init__(self, obj, **kwargs):
        self.kwargs = kwargs
        self.obj = obj


    def play_audio(self, blocking, audio):
        if blocking:
            return self.play_blocking_audio(audio)
        else:
            return self.play_nonblocking_audio(audio)


    def play_blocking_audio(self, audio):
        for sound in audio:
            self.obj.subscribe_event('PlaybackFinished')

            id = uuid.uuid1()
            self.obj.uuids.append(id)

            req_str = self.kwargs['req_base'] + ('channels/%s/play/%s?media=sound:%s' % (self.kwargs['channel_id'], id, sound))
            requests.post(req_str, auth=(self.kwargs['username'], self.kwargs['password']))

            while True:
                time.sleep(0.3)
                if self.obj.eventDict['PlaybackFinished']['status']:
                    self.obj.unsubscribe_event('PlaybackFinished')
                    break

        return {'PlaybackFinished': True}


    def play_nonblocking_audio(self, audio):
        for sound in audio:
            id = uuid.uuid1()
            self.obj.uuids.append(id)

            req_str = self.kwargs['req_base'] + ('channels/%s/play/%s?media=sound:%s' % (self.kwargs['channel_id'], id, sound))
            requests.post(req_str, auth=(self.kwargs['username'], self.kwargs['password']))

        return {'PlaybackFinished': True}


    def delete_audio(self, uuids):
        for id in uuids:
            req_str = self.kwargs['req_base'] + ("playbacks/%s" % (id))
            requests.delete(req_str, auth=(self.kwargs['username'], self.kwargs['password']))
