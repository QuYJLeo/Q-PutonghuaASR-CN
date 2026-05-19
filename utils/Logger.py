import logging.config
import os
from logging import Logger

import yaml

def loadLoggingConfig():
    logging.setLoggerClass(Logger)
    log_conf = 'logging.config.yaml'
    with open(log_conf, 'rt') as f:
        config = yaml.safe_load(f.read())
    handlers = config.get("handlers")
    if handlers is not None:
        for key, value in handlers.items():
            filename = value.get("filename")
            if filename is not None:
                mkdir = filename[:filename.rfind("\\")]
                if not os.path.exists(mkdir):
                    print("创建日志目录：%s" % mkdir)
                    os.makedirs(mkdir)
    logging.config.dictConfig(config)
    logging.setLoggerClass(Logger)
