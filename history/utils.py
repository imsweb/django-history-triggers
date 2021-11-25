from django.apps import apps
from django.conf import settings


def get_history_model():
    return apps.get_model(
        getattr(settings, "HISTORY_MODEL", "history.ObjectHistory"),
        require_ready=False,
    )


def get_request_context(request):
    try:
        field = get_history_model().USER_FIELD
        return {field: request.user} if field else {}
    except AttributeError:
        return {}
