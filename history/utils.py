from django.utils.safestring import mark_safe

from . import backends, conf


def get_history_user_id(request):
    user = getattr(request, conf.REQUEST_USER_FIELD)
    return (
        getattr(user, conf.REQUEST_USER_ATTRIBUTE)
        if conf.REQUEST_USER_ATTRIBUTE
        else user
    )


def json_format(obj, linesep="<br />", valsep=" &rarr; ", arrsep=", "):
    if not isinstance(obj, dict):
        return obj
    lines = []
    for key in sorted(obj):
        value = obj[key]
        if isinstance(value, (list, tuple)):
            formatted_value = arrsep.join(str(v) for v in value)
        else:
            formatted_value = str(value)
        lines.append("{}{}{}".format(key, valsep, formatted_value))
    return mark_safe(linesep.join(lines))


def get_history_model(model_class):
    backend = backends.get_backend()
    return backend.historical_model(model_class)
