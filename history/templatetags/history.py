from django import template
from django.utils.safestring import mark_safe

register = template.Library()


def json_format(obj, linesep="<br />", valsep=" = ", arrsep=", "):
    if obj is None:
        return ""
    if not isinstance(obj, dict):
        return obj
    lines = []
    for key in sorted(obj):
        value = obj[key]
        if value in (None, ""):
            continue
        if isinstance(value, (list, tuple)):
            formatted_value = arrsep.join(str(v) for v in value)
        else:
            formatted_value = str(value)
        lines.append("{}{}{}".format(key, valsep, formatted_value))
    return mark_safe(linesep.join(lines))


@register.simple_tag
def format_json(obj, linesep="<br />", valsep=" = ", arrsep=", "):
    return json_format(obj, linesep=linesep, valsep=valsep, arrsep=arrsep)
