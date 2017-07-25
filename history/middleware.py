"""
Middleware that creates a temporary table for a connection and puts the current User ID in there.
"""

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed

from .utils import create_history_table, get_history_user_id


NOT_SET = object()


class HistoryMiddleware (object):

    def __init__(self, get_response=None):
        if 'postgresql' not in settings.DATABASES['default']['ENGINE']:
            raise MiddlewareNotUsed()
        self.get_response = get_response

    def __call__(self, request):
        response = None
        if hasattr(self, 'process_request'):
            response = self.process_request(request)
        if not response:
            response = self.get_response(request)
        if hasattr(self, 'process_response'):
            response = self.process_response(request, response)
        return response

    def process_request(self, request):
        ignore_paths = getattr(settings, 'HISTORY_MIDDLEWARE_IGNORE', NOT_SET)
        if ignore_paths is NOT_SET:
            ignore_paths = []
            if settings.STATIC_URL:
                ignore_paths.append(settings.STATIC_URL)
            if settings.MEDIA_URL:
                ignore_paths.append(settings.MEDIA_URL)
        for prefix in ignore_paths:
            if request.path.startswith(prefix):
                return
        user_id = get_history_user_id(request)
        if user_id is not None:
            create_history_table(user_id)
