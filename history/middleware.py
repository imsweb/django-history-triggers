from . import backends, conf
from .utils import get_history_user_id


class HistoryMiddleware:
    """
    Middleware that creates a temporary table for a connection and puts the current
    User ID in there.
    """

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        backend = None

        create_history = True
        for prefix in conf.MIDDLEWARE_IGNORE:
            if prefix and request.path.startswith(prefix):
                create_history = False

        if create_history:
            user_id = get_history_user_id(request)
            if user_id is not None:
                backend = backends.get_backend()
                backend.set_user(user_id)

        response = self.get_response(request)

        # Need to make sure we drop the history table after each request, since
        # connections can be re-used in later versions of Django.
        if backend:
            backend.clear_user()

        return response
