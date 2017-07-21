from django.conf import settings
from django.db import connections


def get_history_user_id(request):
    request_user_field = getattr(settings, 'HISTORY_REQUEST_USER_FIELD', 'user')
    user_attribute = getattr(settings, 'HISTORY_REQUEST_USER_ATTRIBUTE', 'pk')
    user = getattr(request, request_user_field)
    return getattr(user, user_attribute) if user_attribute else user


def create_history_table(user_id):
    params = {
        'table': getattr(settings, 'HISTORY_USER_TEMP_TABLE', 'history_user'),
        'field': getattr(settings, 'HISTORY_USER_FIELD', 'user_id'),
        'type': getattr(settings, 'HISTORY_USER_TYPE', 'integer'),
    }
    c = connections['default'].cursor()
    c.execute("""
        CREATE TEMPORARY TABLE IF NOT EXISTS %(table)s (
            %(field)s %(type)s UNIQUE NOT NULL
        )
    """ % params)
    c.execute("TRUNCATE %(table)s" % params)
    c.execute("INSERT INTO %(table)s (%(field)s) VALUES (%%s)" % params, (user_id,))
