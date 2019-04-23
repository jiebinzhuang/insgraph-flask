import os
from flask import Response,Flask, request
from flask_cors import CORS
from insgraph import util, instagram


def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    print("zhuangjb flask start.....:"+__name__)
    CORS(app)
    app.config.from_mapping(
        # a default secret that should be overridden by instance config
        SECRET_KEY='dev',
        # store the database in the instance folder
        DATABASE=os.path.join(app.instance_path, 'insgraph.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.update(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    @app.before_request
    def option_replay():
        if request.method =='OPTIONS':
            resp = Response('')
            print('xxx')
            resp.headers['Access-Control-Allow-Origin'] = '*'
            resp.headers['Access-Control-Allow-Headers'] = '*'
            resp.headers['Access-Control-Request-Method'] = request.headers['Access-Control-Request-Method']
            return resp

    # @app.after_request
    # def set_allow_origin(resp):
    #     h = resp.headers
    #     if request.method != 'OPTIONS' and 'Origin' in request.headers:
    #         h['Access-Control-Allow-Origin'] = request.headers['Origin']

    # register the database commands
    from insgraph import db
    db.init_app(app)

    # apply the blueprints to the app
    from insgraph import auth, user,case
    app.register_blueprint(auth.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(case.bp)
    app.register_blueprint(instagram.bp)

    # make url_for('index') == url_for('blog.index')
    # in another app, you might define a separate main index here with
    # app.route, while giving the blog blueprint a url_prefix, but for
    # the tutorial the blog will be the main index
    app.add_url_rule('/', endpoint='index')

    return app
