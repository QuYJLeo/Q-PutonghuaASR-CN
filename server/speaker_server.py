import collections
import logging
import threading
import time

import eventlet
import pyaudio

from server.session_server import SessionServer
from utils.AudioSpeaker import AudioSpeaker

_log = logging.getLogger(__name__)

logging.basicConfig(level=logging.DEBUG)


class SpeakerServer(SessionServer):
    def __init__(self, host='0.0.0.0', port=5000, cors_origins='*', static_files=None):
        super().__init__(host, port, cors_origins, static_files)

    def program_receive_data(self, speaker, data):
        # print(data)
        speaker.append(data["voice"])

    def initProgram(self, sid, config):
        super().initProgram(sid,config)
        speaker = AudioSpeaker()
        speaker.initSpeaker()
        return speaker

    def destroyProgram(self, program):
        super().destroyProgram(program)
        ...
