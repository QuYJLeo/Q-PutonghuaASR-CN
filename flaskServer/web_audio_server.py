import glob
import json
import logging
import os.path
import time
import uuid

from flask import request
from mutagen import File

from flaskServer.Hs_flask_server import webServer
from flaskServer.web_base_server import WebBaseServer
from utils.AudioUploadFile import AudioUploadFileProcess

from utils.Config import UPLOAD_FOLDER

_log = logging.getLogger(__name__)


class WebAudioServer(WebBaseServer):
    """
    WebUserServer 类用于处理用户上传音频文件和查询音频任务的状态。

    核心功能：
    - 处理用户上传的音频文件
    - 查询音频任务的状态

    使用方式：
    - 构造函数：初始化 WebUserServer 实例，并设置处理音频上传和查询的端点。
    - uploadAudioWav 方法：处理 POST 请求，接收音频文件并保存到服务器。
    - queryAudioTask 方法：处理 POST 请求，查询指定任务 ID 的音频任务状态。

    构造函数参数：
    - 无

    使用限制或潜在的副作用：
    - 音频文件上传时，文件名会包含一个随机生成的 UUID 和属性值。
    - 查询任务状态时，如果任务 ID 不存在，会返回错误信息。
    """

    def __init__(self):
        super().__init__()
        self.uploadDirname = UPLOAD_FOLDER
        webServer.addEndpoint('/uploadAudioWav', '/uploadAudioWav', self.uploadAudioWav, methods=['POST'])
        webServer.addEndpoint('/queryAudioTask', '/queryAudioTask', self.queryAudioTask, methods=['POST'])
        self.fileProcess = AudioUploadFileProcess()

    def uploadAudioWav(self):
        try:
            start_time = time.time()
            random_uuid = uuid.uuid4().hex
            file_path = os.path.join(self.uploadDirname, random_uuid)
            request.files['wavFile'].save(file_path)
            audio = File(file_path)
            assert audio.info.sample_rate == 16000, Exception("Sample rate must be 16000")
            assert any("wav" in mime_type for mime_type in audio.mime), Exception("File format must be wav")
            self.fileProcess.submit(file_path)  # 任务提交给线程池
            _log.info(f"uploadAudioWav success:{random_uuid}，spendTime:{time.time() - start_time} ,file info:{audio.info.__dict__} ")
            return self.success(random_uuid)
        except (AssertionError, Exception) as ex:
            _log.error(f"uploadAudioWav error:{ex}")
            return self.error(str(ex))

    def queryAudioTask(self):
        start_time = time.time()
        task_id = request.json.get("taskId")
        is_details = request.json.get("isDetails", False)  # 默认为 False
        try:
            task_files = glob.glob(os.path.join(self.uploadDirname, f"{task_id}*"))
            assert task_files, Exception("Task ID not found")

            file_name = os.path.join(self.uploadDirname, f"{task_id}.txt")

            if os.path.exists(file_name):
                with open(file_name, 'r', encoding="utf-8") as file:
                    lines_data = [json.loads(line) for line in file]
            else:
                lines_data = []

            text_data = [item for item in lines_data if "final_text" in item]
            text = text_data if is_details else "".join(item["final_text"] for item in text_data)

            status = lines_data[-1].get("status", "processing") if lines_data else "processing"
            error_ = lines_data[-1].get("message") if lines_data else None
            if status == "error":
                raise Exception(error_)

            result = {"status": status, "text": text}
            _log.info(f"queryAudioTask success:{task_id}，spendTime:{time.time() - start_time}")
            return self.success({"result": result})
        except Exception as ex:
            _log.error(f"queryAudioTask error: {ex}")
            return self.error(str(ex))


webAudioServer = WebAudioServer()
