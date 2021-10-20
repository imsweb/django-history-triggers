from . import backends, conf


def get_history_user_id(request):
    user = getattr(request, conf.REQUEST_USER_FIELD)
    return (
        getattr(user, conf.REQUEST_USER_ATTRIBUTE)
        if conf.REQUEST_USER_ATTRIBUTE
        else user
    )


def get_user(user_id):
    from django.contrib.auth import get_user_model

    kwargs = {conf.REQUEST_USER_ATTRIBUTE: user_id}
    return get_user_model().objects.get(**kwargs)


def get_history_model(model_class):
    backend = backends.get_backend()
    return backend.historical_model(model_class)
