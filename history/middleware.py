from django.utils.module_loading import import_string

from . import backends, conf


class HistoryMiddleware:
    """
    Middleware that creates a temporary table for a connection and puts the current
    User ID in there.
    """

    def __init__(self, get_response=None):
        self.get_response = get_response
        self.get_user = (
            conf.REQUEST_USER
            if callable(conf.REQUEST_USER)
            else import_string(conf.REQUEST_USER)
        )

    def __call__(self, request):
        for prefix in conf.MIDDLEWARE_IGNORE:
            if prefix and request.path.startswith(prefix):
                return self.get_response(request)

        backend = backends.get_backend()
        with backend.session(self.get_user(request)):
            return self.get_response(request)
