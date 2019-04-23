import json


from flask import Response

def success():
    response = {
        'status': 'success',
        'msg': '成功'
    }
    return json.dumps(response)


def success(data):
    response = {
        'status': 'success',
        'msg': '成功',
        'data': data
    }
    return json.dumps(response)


def error(fail_msg):
    response = {
        'status': 'error',
        'msg': fail_msg
    }
    return json.dumps(response)


def Response_headers(content):
    resp = Response(content)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp
