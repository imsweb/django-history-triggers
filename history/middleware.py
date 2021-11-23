from django.utils.module_loading import import_string

from . import backends, conf


class HistoryMiddleware:
    """
    Middleware that creates a temporary table for a connection and puts the current
    User ID in there.
    """

    def __init__(self, get_response=None):
        self.get_response = get_response
        self.get_context = (
            conf.REQUEST_CONTEXT
            if callable(conf.REQUEST_CONTEXT)
            else import_string(conf.REQUEST_CONTEXT)
        )

    def __call__(self, request):
        for prefix in conf.MIDDLEWARE_IGNORE:
            if prefix and request.path.startswith(prefix):
                return self.get_response(request)

        backend = backends.get_backend()
        context = self.get_context(request) or {}
        with backend.session(**context):
            return self.get_response(request)
