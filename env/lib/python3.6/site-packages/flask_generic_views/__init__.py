"""
    flask_generic_view
    ===================

    A set of generic class-based views for the Flask microframework inspired by
    the ones in Django.

    :copyright: (c) 2015 Daniel Knell
    :license: BSD, see LICENSE for more information.
"""

from flask_generic_views.core import (FormView, MethodView, RedirectView,
                                      TemplateView, View)

__all__ = ('FormView', 'MethodView', 'RedirectView', 'TemplateView', 'View')

__version__ = '0.1.1'
