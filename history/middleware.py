"""
Middleware that creates a temporary table for a connection and puts the current User ID in there.
"""

from django.db import connections
from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed

def temp_table_exists(c, name):
    c.execute("""
        SELECT EXISTS (SELECT 1 FROM information_schema.tables
        WHERE table_name = %s and table_type = 'LOCAL TEMPORARY')
    """, (name,))
    return c.fetchone()[0]

def create_history_table(user_id):
    params = {
        'table': getattr(settings, 'HISTORY_USER_TEMP_TABLE', 'history_user'),
        'field': getattr(settings, 'HISTORY_USER_FIELD', 'user_id'),
    }
    c = connections['default'].cursor()
    if not temp_table_exists(c, params['table']):
        # TODO: It would be nice to just use IF NOT EXISTS, but it was not implemented until PostgreSQL 9.1.
        c.execute("""
            CREATE TEMPORARY TABLE %(table)s (
                %(field)s integer UNIQUE NOT NULL
            )
        """ % params)
    c.execute("TRUNCATE %(table)s" % params)
    c.execute("INSERT INTO %(table)s (%(field)s) VALUES (%%s)" % params, (user_id,))

class HistoryMiddleware (object):

    def __init__(self):
        if 'postgresql' not in settings.DATABASES['default']['ENGINE']:
            raise MiddlewareNotUsed()

    def process_request(self, request):
        request_user_field = getattr(settings, 'HISTORY_REQUEST_USER_FIELD', 'user')
        assert hasattr(request, request_user_field), "HistoryMiddleware expected to find request.%s" % request_user_field
        user = getattr(request, request_user_field, None)
        static_files_url = settings.STATIC_URL if getattr(settings, 'STATIC_URL', None) else getattr(settings, 'MEDIA_URL', None)
        if user and hasattr(user, 'pk') and user.pk and not request.path.startswith(static_files_url):
            create_history_table(user.pk)
