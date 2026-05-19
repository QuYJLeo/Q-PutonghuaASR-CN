from ASR.offline import AsrOneFlow
from ASR.streaming import ASRFlow
from ASR.streaming2offline import StreamingToOffline
import threading
import time
from datetime import datetime

def audio_capture_fun():
    import pyaudio
    # import numpy as np

    CHUNK = 8000  # 0.6

    # 打开音频流
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,  # 16bit编码格式
                    channels=1,  # 声道数 （1、2）
                    rate=16000,  # 采样频率
                    input=True,
                    frames_per_buffer=CHUNK)  # 每个数据块的大小

    print("开始录音...")
    try:
        while True:
            startTime = time.time() * 1000  # ms
            audio_data = stream.read(CHUNK)
            # audio_data = np.frombuffer(audio_data, dtype=np.int16)[0::2].tobytes()
            # audio_right = np.frombuffer(audio_data, dtype=np.int16)[1::2].tobytes()
            data = {
                "times": startTime,
                "voice": audio_data,
            }
            model.push_data(data)
    except KeyboardInterrupt:
        print("停止录音...")
        model.stop()

    # 关闭音频流
    stream.stop_stream()
    stream.close()
    p.terminate()


def singleton_capture_fun():
    import pyaudio
    import numpy as np

    CHUNK = 1000

    # 打开音频流
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,  # 16bit编码格式
                    channels=2,  # 声道数 （1、2）
                    rate=16000,  # 采样频率
                    input=True,
                    frames_per_buffer=CHUNK)  # 每个数据块的大小


    print("开始录音...")
    input = {}
    try:
        while True:
            audio_data = stream.read(CHUNK)
            audio_left = np.frombuffer(audio_data, dtype=np.int16)[0::2]
            audio_right = np.frombuffer(audio_data, dtype=np.int16)[1::2]
            left_sum = audio_left.sum()
            right_sum = audio_right.sum()
            if left_sum == right_sum == 0:
                continue

            label = find_voice(left_sum, right_sum)
            data = None
            if label == "left":
                data = audio_left
            elif label == "right":
                data = audio_right

            if input == {}:
                input[label] = data
            else:
                assert len(input) == 1
                if label in input.keys():
                    input[label] = np.concatenate((input[label], data))
                else:  #
                    voice = list(input.values())[0]
                    voice_bytes = voice.tobytes()

                    input.clear()
                    input[label] = data

                    startTime = time.time() * 1000  # ms
                    pushDatas = {
                        "times": startTime,
                        "track": label,
                        "voice": voice_bytes,
                    }
                    model.push_data(pushDatas)

    except KeyboardInterrupt:
        print("停止录音...")
        model.stop()

    # 关闭音频流
    stream.stop_stream()
    stream.close()
    p.terminate()


def find_voice(left_sum, right_sum):
    if left_sum == 0 and right_sum != 0:
        return "right"
    if right_sum == 0 and left_sum != 0:
        return "left"

    if right_sum != 0 and left_sum != 0:
        if abs(left_sum) >= abs(right_sum):
            return "left"
        else:
            return "right"




def print_result(result):
    print(result)
    # if result['is_final']:
    #     print("\n======================================================================================================")
    #     print("\t\t火神: ", result)
    #     print("======================================================================================================\n")
    # else:
    #     print(result)


if __name__ == "__main__":

    # 离线demo
    def callback(res):
        print(datetime.now().strftime('%Y-%m-%d %H:%M:%S'), res)
    model = AsrOneFlow(use_gpu=False)
    hotwordspath = "./asr-hotwords.txt"
    model.setListener(callback)
    model.setHotwords(hotwordspath)
    model.flow(wav_path='4.33.wav')
    exit()


    # # 在线 demo
    # model = ASRFlow()
    # model.setListener(print_result)
    # read_thread = threading.Thread(target=audio_capture_fun, daemon=True)
    # read_thread.start()
    # model.start()
    # while True:
    #     time.sleep(1)


    # 在线转离线 demo
    model = StreamingToOffline()
    model.setListener(print_result)
    hotwordspath = "./asr-hotwords.txt"
    model.setHotwords(hotwordspath)
    read_thread = threading.Thread(target=audio_capture_fun, daemon=True)
    read_thread.start()
    model.start()
    while True:
        time.sleep(1)
