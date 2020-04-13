from flask import Flask, request, g, Response
from src.errorhandlers import page_is_forbidden, page_not_found,\
                            page_was_deleted, httpmethod_not_allowed,\
                            server_error
from src.estimator_blueprint import estimate_blueprint
from src.configs import ProductionConfig
from datetime import datetime


def create_app(enviroment, configfile=None):

    # Creates an instance app of the flask class

    app = Flask(__name__, instance_relative_config=True)

    # Loads configuration from the configurations class
    # And updates config dictinary.

    app.config.from_object(enviroment)

    # Loads a key value pair from a configfile to
    # override some of the configuration from the
    # main configurations.

    app.config.from_pyfile(configfile, silent=True)

    # Registers blueprints

    app.register_blueprint(estimate_blueprint)

    # register application exceptions

    app.register_error_handler(404, page_not_found)

    app.register_error_handler(403, page_is_forbidden)

    app.register_error_handler(410, page_was_deleted)

    app.register_error_handler(500, server_error)

    app.register_error_handler(405, httpmethod_not_allowed)

    return app

# Runs the function and captures the return in app variable

app = create_app(ProductionConfig, 'config.py')

logs = []
# Before and after requests logs endpoint


@app.route(
    '/api/v1/on-covid-19/logs', methods=['GET']
)
def requests_logs():

    """This endpoint returns all requests and responses logs"""

    string_logs = ''

    for log in logs:
        string_logs += log
    text_response = Response(
        string_logs,
        status=200, mimetype='text/plain'
    )
    return text_response

# All requests to the app


@app.before_request
def before_a_request():

    """This Logs all requests issued in the app"""

    g.request_start_time = datetime.now()
    g.log_string = '{}   {}  '.format(request.method, request.path)


@app.after_request
def after_a_request(response):

    """This Logs all requests issued in the app"""

    global logs

    g.request_time = datetime.now() - g.request_start_time

    g.log_string = '{}{}  {}ms\n'.format(
        g.log_string, response.status_code,
        g.request_time.microseconds
    )

    logs.append(g.log_string)

    return response

# Runs the app

if __name__ == "__main__":

    app.run()