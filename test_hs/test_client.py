# 示例用法（可以放在另一个文件中，例如 main.py）
import logging
import queue
import threading
import time

from client.socket_io_client import SocketIOClient
from test_hs.audio_recorder2 import AudioRecorder

_log = logging.getLogger(__name__)
SERVER_URL = 'http://192.168.1.233:6060'  # 你的服务器地址
d_left = queue.Queue()
d_right = queue.Queue()


def client_left():
    # 创建客户端实例
    client1 = SocketIOClient(SERVER_URL)
    client1.setConnectListener(print)
    client1.setDisconnectListener(print)
    client1.setCommandListener(print)
    client1.setMessageListener(print)
    client1.setNoticeListener(print)
    if client1.connect():
        print("client_left.connect()")
        client1.sendCommand({"command": "START", "config": {"offline": 1}})
        while True:
            data = d_left.get()
            if data:
                client1.sendVoice(int(time.time() * 1000 - 50), data)
    else:
        print("Failed to connect. Exiting.")


def client_right():
    clent2 = SocketIOClient(SERVER_URL)
    clent2.setConnectListener(print)
    clent2.setDisconnectListener(print)
    clent2.setCommandListener(print)
    clent2.setMessageListener(print)
    clent2.setNoticeListener(print)

    # 连接到服务器
    if clent2.connect():
        # 发送消息
        clent2.sendCommand({"command": "START", "config": {"offline": 1}})
        while True:
            data = d_right.get()
            if data:
                clent2.sendVoice(int(time.time() * 1000 - 50), data)
    else:
        print("Failed to connect. Exiting.")


if __name__ == '__main__':
    recorder = AudioRecorder()  # 移除 record_second


    def audio_callback(data, left=None, right=None):
        d_left.put(left)
        d_right.put(right)


    threading.Thread(target=client_left).start()
    threading.Thread(target=client_right).start()

    recorder.setAudioListener(audio_callback)
    recorder.start()

    time.sleep(10000)
