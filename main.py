from flaskServer.Hs_flask_server import webServer
from server.asr_server import AsrServer
from utils.Logger import loadLoggingConfig
from utils.Config import SOCKET_IO_HOST, SOCKET_IO_PORT, SOCKET_IO_CORS_ORIGINS, SOCKET_IO_STATIC_FILES, IS_SERVER
from utils.TestUtil import testUtil

if __name__ == '__main__':
    import multiprocessing

    multiprocessing.freeze_support()
    multiprocessing.set_start_method('spawn', force=True)

    loadLoggingConfig()
    if IS_SERVER:
        assert testUtil.check(), Exception("license 授权失败")
    asr_server = AsrServer(
        host=SOCKET_IO_HOST,
        port=SOCKET_IO_PORT,
        cors_origins=SOCKET_IO_CORS_ORIGINS,
        static_files=SOCKET_IO_STATIC_FILES
    )
    from flaskServer.web_audio_server import webAudioServer

    webServer.start()  # 启动http服务器
    asr_server.start()  # 启动socketio服务器
    asr_server.join()
