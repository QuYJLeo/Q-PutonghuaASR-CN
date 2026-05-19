from flask import make_response, jsonify


class WebBaseServer:
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
