import logging
import os
from threading import Thread
from utils.TestUtil import testUtil
from flask import Flask, make_response, jsonify
from gevent.pywsgi import WSGIServer

from utils.Config import WEB_PORT, WEB_HOST, IS_SERVER

_log = logging.getLogger(__name__)


class FlaskServer(Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.port = int(WEB_PORT)
        self.host = WEB_HOST
        self.app = Flask(__name__)
        self.server = None

        def license_permit():
            if IS_SERVER is True:
                if not testUtil.check():
                    response = make_response(jsonify({
                        "code": 401,
                        "message": "License 授权失败,已过有效期",
                    }))
                    response.status_code = 401
                    response.headers['WWW-Authenticate'] = 'License Auth fail'
                    return response
        self.app.before_request(license_permit)

    def success(self, data):
        response = make_response(jsonify({
            "code": 0,
            "data": data
        }))
        return response

    def error(self, msg, code=500):
        response = make_response(jsonify({
            "code": code,
            "message": msg
        }))
        response.status_code = code
        return response

    def addEndpoint(self, endpoint=None, endpoint_name=None, handler=None, **options):
        _log.debug("注册路由：%s %s %s %s" % (endpoint, endpoint_name, handler, options))
        self.app.add_url_rule(endpoint, endpoint_name, handler, **options)

    def run(self):
        _log.info("启动WEB服务端口：%s" % self.port)
        self.server = WSGIServer((self.host, self.port), self.app)
        self.server.serve_forever()


webServer = FlaskServer()
