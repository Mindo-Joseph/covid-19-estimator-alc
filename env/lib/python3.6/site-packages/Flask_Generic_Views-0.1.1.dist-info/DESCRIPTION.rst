
Flask-Generic-Views
===================

Flask-Generic-Views is a set of generic class-based views for the Flask
microframework inspired by the ones in Django.

.. code:: python

    from flask import Flask
    from flask.ext.generic_views import TemplateView

    app = Flask(__name__)

    index_view = TemplateView.as_view('index', template_file='index.html')

    app.add_url_rule('/', index_view)

    if __name__ == '__main__':
        app.run()

Database Support
----------------

Currently Flask-Generic-Views supports use of Models created with SQLAlchemy.

Installation
------------

To install the basic views:

.. code:: bash

    $ pip install flask-generic-views

To install optional SQLAlchemy support:

.. code:: bash

    $ pip install flask-generic-views[sqlalchemy]

To install all optional packages:

.. code:: bash

    $ pip install flask-generic-views[all]

Links
-----

* `Documentation <https://flask-generic-views.readthedocs.org/>`_
* `GitHub <https://github.com/artisanofcode/flask-generic-views>`_


