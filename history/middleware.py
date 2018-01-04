"""
Middleware that creates a temporary table for a connection and puts the current User ID in there.
"""

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed

from .utils import create_history_table, drop_history_table, get_history_user_id


NOT_SET = object()


class HistoryMiddleware (object):

    def __init__(self, get_response=None):
        if 'postgresql' not in settings.DATABASES['default']['ENGINE']:
            raise MiddlewareNotUsed()
        self.get_response = get_response
        self.ignore_paths = getattr(settings, 'HISTORY_MIDDLEWARE_IGNORE', NOT_SET)
        if self.ignore_paths is NOT_SET:
            self.ignore_paths = []
            if settings.STATIC_URL:
                self.ignore_paths.append(settings.STATIC_URL)
            if settings.MEDIA_URL:
                self.ignore_paths.append(settings.MEDIA_URL)

    def __call__(self, request):
        create_history = True
        for prefix in self.ignore_paths:
            if request.path.startswith(prefix):
                create_history = False

        if create_history:
            user_id = get_history_user_id(request)
            if user_id is not None:
                create_history_table(user_id)

        response = self.get_response(request)

        # Need to make sure we drop the history table after each request, since connections can be re-used in later
        # versions of Django.
        drop_history_table()

        return response
