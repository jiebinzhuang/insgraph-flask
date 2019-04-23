import json

from flask import (
    Blueprint, flash, redirect, request, session, url_for
)

from insgraph import util
from insgraph.db import get_db
from insgraph.utils import httputil

bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/info', methods=['GET', 'POST'])
def login():
    print("user info")
    token = request.args.get("token")
    db = get_db()
    error = None
    user = db.execute(
        'SELECT * FROM user WHERE id = ?', (token,)
    ).fetchone()
    if user is None:
        error = 'Incorrect username.'

    if error is None:
        # store the user id in a new session and return to the index
        # 默认全部是管理员 角色后面再实现
        response = {
            'roles': ['admin'],
            'token': token,
            'avatar': 'https://wpimg.wallstcn.com/f778738c-e4f8-4870-b634-56703b4acafe.gif',
            'name': user['username']
        }
        content = json.dumps(response)
        return util.Response_headers(content)
        # return httputil.success(user['id'])
    flash(error)
    return httputil.error(error)


@bp.route('/logout')
def logout():
    """Clear the current session, including the stored user id."""
    session.clear()
    return redirect(url_for('index'))
