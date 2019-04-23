better-tp
=========

The basic blog app built in the Flask `tutorial`_.

.. _tutorial: http://flask.pocoo.org/docs/tutorial/


Install
-------

**Be sure to use the same version of the code as the version of the docs
you're reading.** You probably want the latest tagged version, but the

    $ cd insgraph-flask

Create a virtualenv and activate it::

    $ python3 -m venv venv
    $ . venv/bin/activate

Or on Windows cmd::

    $ py -3 -m venv venv
    $ venv\Scripts\activate.bat

Install insgraph::

    $ pip install -e .

Or if you are using the master branch, install Flask from source before
installing better-tp::

    $ pip install -e ../..
    $ pip install -e .


Run
---

::

    $ export FLASK_APP=insgraph
    $ export FLASK_ENV=development
    $ flask init-db
    $ flask run

Or on Windows cmd::

    > set FLASK_APP=insgraph
    > set FLASK_ENV=development
    > flask init-db
    > flask run

Open http://127.0.0.1:5000 in a browser.


Test
----

::

    $ pip install '.[test]'
    $ pytest

Run with coverage report::

    $ coverage run -m pytest
    $ coverage report
    $ coverage html  # open htmlcov/index.html in a browser
