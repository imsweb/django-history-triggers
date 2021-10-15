from django.apps import apps
from django.db import models
from django.db.backends.utils import split_identifier, truncate_name

from history import conf
from history.models import HistoricalModel


class HistoryBackend:
    supports_schemas = True

    def __init__(self, connection):
        self.conn = connection

    def get_models(self):
        return apps.get_models(include_auto_created=True)

    def historical_model(self, model):
        user_field = (
            models.IntegerField if "int" in conf.USER_TYPE else models.TextField
        )
        model_attrs = {
            "__module__": "history.models",
            model._meta.pk.name: model._meta.pk.__class__(primary_key=True),
            conf.USER_FIELD: user_field(),
        }
        type_name = "%sHistory" % model.__name__
        meta_name = "%sMeta" % model.__name__
        model_attrs["Meta"] = type(
            meta_name,
            (object,),
            {
                "db_table": self.history_table_name(model._meta.db_table),
                "managed": False,
            },
        )
        return type(type_name, (HistoricalModel,), model_attrs)

    def execute(self, sql, params=None, cursor=None):
        if cursor:
            return cursor.execute(sql, params)
        else:
            with self.conn.cursor() as cursor:
                return cursor.execute(sql, params)

    def set_user(self, user_id):
        params = {
            "table": conf.USER_TEMP_TABLE,
            "field": conf.USER_FIELD,
            "type": conf.USER_TYPE,
        }
        self.execute(
            """
            CREATE TEMPORARY TABLE IF NOT EXISTS %(table)s (
                %(field)s %(type)s UNIQUE NOT NULL
            );
            TRUNCATE %(table)s;
        """
            % params
        )
        self.execute(
            "INSERT INTO %(table)s (%(field)s) VALUES (%%s);" % params, (user_id,)
        )

    def clear_user(self):
        self.execute(
            "DROP TABLE IF EXISTS %(table)s;"
            % {
                "table": conf.USER_TEMP_TABLE,
            }
        )

    def history_table_name(self, name):
        qn = split_identifier(name)[1]
        qn = conf.TABLE_PREFIX + qn + conf.TABLE_SUFFIX
        if conf.SCHEMA_NAME:
            if self.supports_schemas:
                qn = '"{}"."{}"'.format(conf.SCHEMA_NAME, qn)
            else:
                qn = conf.SCHEMA_NAME + "_" + qn
        qn = truncate_name(qn)
        if qn == name:
            raise ValueError("History table name not unique: {}".format(qn))
        return qn

    def trigger_name(self, model, trigger_type, prefix="trig"):
        return truncate_name(
            "{}_{}_{}".format(prefix, model._meta.db_table, trigger_type.name.lower())
        )

    def create_schema(self):
        raise NotImplementedError()

    def drop_schema(self):
        raise NotImplementedError()

    def create_history_table(self, model):
        self.execute(
            """
            CREATE TABLE IF NOT EXISTS %(table)s (
                %(pk_name)s %(pk_type)s not null,
                snapshot %(json_type)s,
                changes %(json_type)s,
                %(user_field)s %(user_type)s,
                event_date %(timestamp_type)s not null,
                event_type char(1) not null
            );
            """
            % {
                "table": self.history_table_name(model._meta.db_table),
                "pk_name": model._meta.pk.name,
                "pk_type": model._meta.pk.rel_db_type(self.conn),
                "timestamp_type": self.conn.data_types["DateTimeField"],
                "json_type": self.conn.data_types["JSONField"],
                "user_field": conf.USER_FIELD,
                "user_type": conf.USER_TYPE,
            }
        )

    def drop_history_table(self, model):
        self.execute(
            "DROP TABLE IF EXISTS %(table)s"
            % {
                "table": self.history_table_name(model._meta.db_table),
            }
        )

    def create_trigger(self, model, trigger_type):
        raise NotImplementedError()

    def drop_trigger(self, model, trigger_type):
        raise NotImplementedError()
