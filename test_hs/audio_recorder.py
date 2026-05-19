import pyaudio
import numpy as np
import threading
import time
import wave
import queue  # 用于线程间通信


class AudioRecorder:
    def __init__(self, sample_rate=16000):  # 移除 record_seconds
        self.chunk_size = int(sample_rate * 30 / 1000)
        self.sample_rate = sample_rate
        self.is_running = False
        self.audio_queue = queue.Queue()  # 用于存放音频数据
        self.p = pyaudio.PyAudio()
        self.stream = None  # stream 初始化为 None
        self.listener = None
        self.recording_thread = None
        self.push_thread = None

    def setAudioListener(self, listener):
        self.listener = listener

    def start(self):
        self.is_running = True
        self.recording_thread = threading.Thread(target=self._record_loop)
        self.recording_thread.daemon = True
        self.recording_thread.start()

        self.push_thread = threading.Thread(target=self._push_loop)
        self.push_thread.daemon = True
        self.push_thread.start()
        print("音频录制开始...")

    def stop(self):
        self.is_running = False
        if self.recording_thread.is_alive():
            self.recording_thread.join()  # 等待录音线程结束

        if self.push_thread.is_alive():
            self.push_thread.join()  # 等待录音线程结束

        if self.stream:  # 检查 stream 是否已经被打开
            self.stream.stop_stream()
            self.stream.close()
        print("音频录制停止.")
        self.p.terminate()

    def _callback(self, in_data, frame_count, time_info, status):
        """
        PyAudio stream callback function.
        """
        try:
            self.audio_queue.put(in_data)  # 将音频数据放入队列
            return (None, pyaudio.paContinue)
        except Exception as e:
            print(f"Callback 错误: {e}")
            return (None, pyaudio.paAbort)

    def _record_loop(self):
        try:
            self.stream = self.p.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=self.sample_rate,
                                      input=True,
                                      frames_per_buffer=self.chunk_size,
                                      stream_callback=self._callback) # 使用 stream_callback

            self.stream.start_stream() # 启动 stream

            while self.is_running:
                time.sleep(0.1)  # 保持线程运行, 避免过快退出. 可以根据需要调整.

            self.stream.stop_stream() # 确保停止 stream
            self.stream.close()


        except Exception as e:
            print(f"PyAudio 流错误: {e}")


    def _push_loop(self):
        while True:
            try:
                audioData = self.audio_queue.get(timeout=1)
                if self.listener:
                    self.listener(audioData, audioData, audioData)
            except queue.Empty:  # 超时异常，队列为空
                if not self.is_running:
                    break # 退出推送循环
                continue
            except Exception as e:
                print(f"推送错误: {e}")
                break

    def is_recording(self):
        return self.is_running