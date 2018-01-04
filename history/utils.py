from django.conf import settings
from django.db import connections, models

from . import conf


def get_history_user_id(request):
    user = getattr(request, conf.REQUEST_USER_FIELD)
    return getattr(user, conf.REQUEST_USER_ATTRIBUTE) if conf.REQUEST_USER_ATTRIBUTE else user


def create_history_table(user_id):
    params = {
        'table': conf.USER_TEMP_TABLE,
        'field': conf.USER_FIELD,
        'type': conf.USER_TYPE,
    }
    c = connections['default'].cursor()
    c.execute("""
        CREATE TEMPORARY TABLE IF NOT EXISTS %(table)s (
            %(field)s %(type)s UNIQUE NOT NULL
        )
    """ % params)
    c.execute("TRUNCATE %(table)s" % params)
    c.execute("INSERT INTO %(table)s (%(field)s) VALUES (%%s)" % params, (user_id,))


def drop_history_table():
    c = connections['default'].cursor()
    c.execute("DROP TABLE IF EXISTS %(table)s" % {
        'table': conf.USER_TEMP_TABLE,
    })
