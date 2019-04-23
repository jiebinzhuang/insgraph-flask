import json
import os
import shutil

from flask import (
    Blueprint, request, send_from_directory,
    make_response)

from insgraph.db import get_db
from insgraph.utils import httputil

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


