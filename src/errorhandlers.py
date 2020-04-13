from flask import jsonify


def page_not_found(e):

    """Handles resource wasn't found"""

    return jsonify({
        'status': 404, 'error_message': 'The resorse wasn\'t found'
    }), 404


def page_is_forbidden(e):

    """The resource is for authorised users"""

    return jsonify({
        'status': 403,
        'error_message': 'unauthorised to access the resource'
    }), 403


def httpmethod_not_allowed(e):

    """The Http verb used is not allowed for the request"""

    return jsonify({
        'status': 405,
        'error_message': 'The http method is not allowed'
    }), 405


def page_was_deleted(e):

    """The resource dosen't exists anymore"""

    return jsonify({
        'status': 410,
        'error_message': 'The resource was deleted'
    }), 410


def server_error(e):

    """The server has issues it could be anything"""

    return jsonify({
        'status': 500,
        'error_message': 'The server has some issues'
    }), 500