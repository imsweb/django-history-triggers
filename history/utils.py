from . import backends


def get_request_user(request):
    try:
        return request.user.pk
    except AttributeError:
        return None


def get_history_model(model_class):
    backend = backends.get_backend()
    return backend.historical_model(model_class)
