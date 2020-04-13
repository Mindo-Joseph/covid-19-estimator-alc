from flask import Blueprint, jsonify, request, Response
from src.validator import Validator
from src.estimator import estimator
from dicttoxml import dicttoxml
from datetime import datetime

# creates a blueprint object called estimate_blueprint

estimate_blueprint = Blueprint('estimate', __name__)

# An endpoint for handling estimator POST request


@estimate_blueprint.route(
    '/api/v1/on-covid-19', methods=["GET", "POST"]
)
@estimate_blueprint.route(
    '/api/v1/on-covid-19/<string:dataformat>', methods=["GET", "POST"]
)
def estimator_endpoint(dataformat=None):

    """An endpoint to handle estimator data posted"""

    # required form keys

    form_keys = (
        "periodType", "timeToElapse", "region",
        "reportedCases", "population", "totalHospitalBeds"
    )

    # If the request is a post request

    if request.method == "POST":

        # Gets form data and converts it to a dict

        data = request.get_json()

        # Validating the form data, for keys and values

        formValues = Validator.check_empty_values(**data)

        formKeys = Validator.check_keys(**data)

        formKeysValid = Validator.check_valid_keys(
            *form_keys, **data
        )

        # Tests if the form data are valid

        if not formValues:

            return jsonify({
                'status': 400,
                'error': 'Please provide all values for the form'
            }), 400

        elif not formKeys:

            return jsonify({
                'status': 400,
                'error': 'Please provide all keys for the form'
            }), 400

        elif not formKeysValid:

            return jsonify({
                'status': 400,
                'error': 'Please provide all valid keys for the form'
            }), 400

        else:

            strings_FormData = (data["region"]["name"], data["periodType"])

            formStringsSpaces =\
                Validator.checkAbsoluteSpaceCharacters(
                    *strings_FormData
                )

            if formStringsSpaces:

                return jsonify({
                    'status': 400,
                    'error': 'The form strings values can\'t be spaces'
                }), 400

            else:

                estimatedData = estimator(data)

                # Checks if the path variable matches a json or an xml.

                if dataformat == 'json':

                    return jsonify(estimatedData)

                elif dataformat == 'xml':

                    xml_estimates = dicttoxml(estimatedData)
                    xml_response = Response(
                        xml_estimates,
                        status=200, mimetype='application/xml'
                    )

                    return xml_response

                else:

                    return jsonify(estimatedData)

    return jsonify({
        "status": 200,
        "message": "Post covid-19 data and get the estimates"
    }), 200