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

    def _record_loop(self):
        try:
            # 标记播放状态
            self.is_playing = True
            # 初始化 PyAudio
            p = pyaudio.PyAudio()

            # 打开音频流
            self.stream = p.open(format=pyaudio.paInt16,
                                 channels=1,
                                 rate=self.sample_rate,
                                 output=True)
            # 建议在循环外打开文件，或者在循环内检查文件状态
            wf = wave.open("dx_audio_16k_mono.wav", 'rb')

            while self.is_playing:  # 使用变量控制，方便外部停止
                data = wf.readframes(800*5)
                # 如果读取不到数据，说明到了文件末尾
                if not data or len(data) == 0:
                    wf.rewind()  # 将文件指针重置到开头，实现循环
                    continue  # 跳过本次循环，重新读取开头的数据
                self.audio_queue.put(data)
                self.stream.write(data)
            # 正常退出循环后关闭资源
            wf.close()
            self.stream.stop_stream()
            self.stream.close()
            p.terminate()

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
                    break  # 退出推送循环
                continue
            except Exception as e:
                print(f"推送错误: {e}")
                break

    def is_recording(self):
        return self.is_running
