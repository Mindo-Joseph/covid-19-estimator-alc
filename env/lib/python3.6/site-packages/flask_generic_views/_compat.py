"""
    flask_generic_views._compat
    ===========================

    Some py2/py3 compatibility support based on a stripped down version of six
    so we don't have to depend on a specific version of it.

    :copyright: (c) 2015 Daniel Knell
    :license: BSD, see LICENSE for more information.
"""

import sys

PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str,
    integer_types = int,
    text_type = str
else:
    string_types = basestring,
    integer_types = (int, long)
    text_type = unicode

if PY3:
    def iterkeys(d, **kw):
        return iter(d.keys(**kw))

    def iteritems(d, **kw):
        return iter(d.items(**kw))
else:
    def iterkeys(d, **kw):
        return d.iterkeys(**kw)

    def iteritems(d, **kw):
        return d.iteritems(**kw)
