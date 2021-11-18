from . import backends


def request_user(request):
    try:
        return request.user.pk
    except AttributeError:
        return None


def get_user(user_id):
    from django.contrib.auth import get_user_model

    return get_user_model().objects.get(pk=user_id)


def get_history_model(model_class):
    backend = backends.get_backend()
    return backend.historical_model(model_class)
