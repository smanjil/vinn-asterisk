
import os


def move_files(fnames):
    source_files = '/var/spool/asterisk/recording/'
    destination_files = '/home/ano/voiceinn/voiceinn-web/static/'

    files = os.listdir(source_files)

    for f in fnames:
        if f + '.wav' in files:
            src_fullpath = source_files + "/" + f + '.wav'
            dest_fullpath = destination_files + "/" + f + '.wav'
            os.system("mv " + src_fullpath + " " + dest_fullpath)
