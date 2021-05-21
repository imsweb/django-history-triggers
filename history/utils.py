from django.contrib.postgres.fields import JSONField
from django.db import connections, models
from django.utils.functional import cached_property
from django.utils.safestring import mark_safe

from history.management.commands.triggers import get_base_tables, truncate_long_name

from . import conf


def get_history_user_id(request):
    user = getattr(request, conf.REQUEST_USER_FIELD)
    return (
        getattr(user, conf.REQUEST_USER_ATTRIBUTE)
        if conf.REQUEST_USER_ATTRIBUTE
        else user
    )


def create_history_table(user_id):
    params = {
        "table": conf.USER_TEMP_TABLE,
        "field": conf.USER_FIELD,
        "type": conf.USER_TYPE,
    }
    c = connections["default"].cursor()
    c.execute(
        """
        CREATE TEMPORARY TABLE IF NOT EXISTS %(table)s (
            %(field)s %(type)s UNIQUE NOT NULL
        )
        """
        % params
    )
    c.execute("TRUNCATE %(table)s" % params)
    c.execute("INSERT INTO %(table)s (%(field)s) VALUES (%%s)" % params, (user_id,))


def drop_history_table():
    c = connections["default"].cursor()
    c.execute(
        "DROP TABLE IF EXISTS %(table)s"
        % {
            "table": conf.USER_TEMP_TABLE,
        }
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


class HistoryModelMixin:
    @property
    def transaction_type_formatted(self):
        return {"~": "Modified", "+": "Added", "-": "Removed"}.get(
            self.transaction_type
        )

    @property
    def user_key(self):
        return getattr(self, conf.USER_FIELD)

    def get_user(self):
        if not conf.REQUEST_USER_ATTRIBUTE:
            return None
        from django.contrib.auth import get_user_model

        return get_user_model().objects.get(
            **{conf.REQUEST_USER_ATTRIBUTE: self.user_key}
        )

    @property
    def new_value_formatted(self):
        return json_format(self.new_value)

    @property
    def old_value_formatted(self):
        return json_format(self.old_value)

    @cached_property
    def json_changes(self):
        if not conf.USE_JSON:
            return None
        if not self.old_value or not self.new_value:
            return None
        changes = {}
        all_keys = set(self.old_value.keys()) | set(self.new_value.keys())
        for key in all_keys:
            old = self.old_value.get(key)
            new = self.new_value.get(key)
            if old != new:
                changes[key] = [old, new]
        return changes

    @property
    def changes_formatted(self):
        return json_format(self.json_changes, valsep=": ", arrsep=" &rarr; ")


def get_history_model(model_class):
    cursor = connections["default"].cursor()
    table_names = get_base_tables(cursor)
    pk_name, pk_type = table_names[model_class._meta.db_table]
    history_table = truncate_long_name(model_class._meta.db_table + "_history")
    pk_field = models.IntegerField if pk_type.startswith("int") else models.TextField
    value_field = JSONField if conf.USE_JSON else models.TextField
    user_field = (
        models.IntegerField if conf.USER_TYPE.startswith("int") else models.TextField
    )
    attributes = {
        "__module__": "history",
        pk_name: pk_field(primary_key=True),
        "old_value": value_field(),
        "new_value": value_field(),
        "date_modified": models.DateTimeField(),
        conf.USER_FIELD: user_field(),
        "transaction_type": models.CharField(max_length=1),
    }
    if not conf.USE_JSON:
        attributes["field_name"] = models.CharField(max_length=64)
    type_name = "%sHistory" % model_class.__name__
    meta_name = "%sMeta" % model_class.__name__
    attributes["Meta"] = type(
        meta_name,
        (object,),
        {
            "db_table": '"%s"."%s"' % (conf.SCHEMA_NAME, history_table),
            "managed": False,
        },
    )
    return type(type_name, (models.Model, HistoryModelMixin), attributes)
