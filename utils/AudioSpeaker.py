import logging
import queue
import threading
import time

import pyaudio

_log = logging.getLogger(__name__)


class AudioSpeaker:

    def __init__(self):
        self.stream = None
        self.server_thread = None
        self._queue = queue.Queue()

    def initSpeaker(self, channels=1, sample_rate=16000):
        p = pyaudio.PyAudio()
        self.stream = p.open(format=pyaudio.paInt16,
                             channels=channels,
                             rate=sample_rate,
                             output=True,
                             )  # 设置 output=True 以进行播放

        self.server_thread = threading.Thread(target=self._play, daemon=True, name="_play")
        self.server_thread.start()

    def _play(self):
        while True:
            try:
                data = self._queue.get(timeout=2)
                self.stream.write(data)
            except queue.Empty:
                time.sleep(0.1)

    def append(self, data):
        self._queue.put(data)
