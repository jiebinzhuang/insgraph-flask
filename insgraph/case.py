import json
import os
import shutil

from flask import (
    Blueprint, request, send_from_directory,
    make_response)

from insgraph.db import get_db
from insgraph.utils import httputil
from insgraph.utils.treeutil2 import getTree

bp = Blueprint('caseManagement', __name__, url_prefix='/caseManagement')


@bp.route('/getProjectList', methods=['GET'])
def getProjectList():
    print("getProjectList")
    cds = get_db().execute(
        'SELECT projecct_code FROM project '
    ).fetchall()
    project_list = []
    for cd in cds:
        print(cd[0])
        project_list.append(cd[0])

    content = json.dumps(project_list)
    resp = httputil.Response_headers(content)
    return resp



@bp.route('/downloadXmind', methods=['GET'])
def download_file():
    project_code = request.args.get("projectCode")
    version_code = request.args.get("versionCode")
    directory = os.getcwd()
    print("directory---------------------------project_code:" + project_code)
    print("directory---------------------------version_code:" + version_code)
    #
    shutil.copyfile('demo.xmind', project_code+'.xmind')

    tree_list = getTree(project_code, version_code, '')

    # build_file(project_code,tree_list)


    response = make_response(send_from_directory(directory,  project_code+'.xmind', as_attachment=True))
    response.headers["Content-Disposition"] = "attachment; filename={}".format(project_code+'.xmind'.encode().decode('latin-1'))
    return response

