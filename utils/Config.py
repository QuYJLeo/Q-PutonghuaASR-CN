import os

import yaml

with open('config.yaml', 'rt', encoding="utf-8") as f:
    config = yaml.safe_load(f.read())

SOCKET_IO_HOST = config.get("server").get("host")
SOCKET_IO_PORT = config.get("server").get("port")
SOCKET_IO_CORS_ORIGINS = config.get("server").get("origins")  # 生产环境必须修改
SOCKET_IO_STATIC_FILES = {
    '/': {'content_type': 'text/html', 'filename': 'index.html'}
}

AUTHS = config.get("auths", [])  # 授权内容，以List的形式，兼容多个授权

WEB_PORT = config.get("WEB").get("PORT")
WEB_HOST = config.get("WEB").get("HOST")

# MODEL ASR
SEACO_NUM_THREADS = config.get("MODEL").get("SEACO_NUM_THREADS")
FSMN_NUM_THREADS = config.get("MODEL").get("FSMN_NUM_THREADS")
CT_NUM_THREADS = config.get("MODEL").get("CT_NUM_THREADS")

# 是否为服务端
IS_SERVER = config.get("BASIC", {}).get("IS_SERVER", False)
IS_CUDA = config.get("BASIC", {}).get("IS_CUDA", False)

OFFLINE_LIMIT_SIZE = config.get("BASIC", {}).get("OFFLINE_LIMIT_SIZE", 0)
ONLINE_LIMIT_SIZE = config.get("BASIC", {}).get("ONLINE_LIMIT_SIZE", 0)

# 文件上传
PROCESS_NUM = config.get("FILE").get("ProcessNum")
THRESHOLD_DAY = config.get("FILE").get("thresholdDay")
FILE_UPLOAD_FOLDER = config.get("FILE").get("uploadFolderPath")
UPLOAD_FOLDER = os.path.join(os.getcwd(), FILE_UPLOAD_FOLDER)  # 设置上传文件的保存路径
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
