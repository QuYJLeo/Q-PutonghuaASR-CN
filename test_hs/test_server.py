import logging

from server.socket_io_server import SocketIOServer
from server.speaker_server import SpeakerServer

logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    # 示例用法
    socket_server = SpeakerServer(host='0.0.0.0', port=5000, cors_origins='*', static_files={
        '/': {'content_type': 'text/html', 'filename': 'index.html'}
    })
    socket_server.start()


    # 模拟一些其他的程序逻辑
    import time

    try:
        while True:
            time.sleep(5)
            print("Main thread is running...")
            # socket_server.send_message("my_response", {'data': 'Connected', 'count': 22})
    except KeyboardInterrupt:
        print("Program interrupted. Exiting...")
    finally:
        # 注意：无法在此处安全地停止服务器线程，它将在程序退出时自动结束
        print("Exiting program.")