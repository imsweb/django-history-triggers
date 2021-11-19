from django.apps import apps
from django.db import models
from django.db.backends.utils import split_identifier, truncate_name
from django.utils.module_loading import import_string

from history import conf
from history.models import HistoricalModel


class HistoryBackend:
    supports_schemas = True

    def __init__(self, connection):
        self.conn = connection
        self.user_field = None
        self.user_column = None
        self.user_type = None
        # Get and store the user field, type, and column name.
        model_or_field = (
            conf.USER_MODEL()
            if callable(conf.USER_MODEL)
            else import_string(conf.USER_MODEL)()
        )
        if issubclass(model_or_field, models.Model):
            self.user_field = models.ForeignKey(
                model_or_field,
                db_constraint=False,
                related_name="+",
                on_delete=models.DO_NOTHING,
            )
            self.user_column = conf.USER_FIELD + "_id"
        elif issubclass(model_or_field, models.Field):
            self.user_field = model_or_field
            if self.user_field.db_column:
                # If the custom field specifies a column name, use it.
                self.user_column = self.user_field.db_column
            elif isinstance(self.user_field, models.ForeignKey):
                # ForeignKey columns get suffixed with _id by default.
                self.user_column = conf.USER_FIELD + "_id"
            else:
                # Non-FK fields without a db_column just use the attribute name.
                self.user_column = conf.USER_FIELD
        if self.user_field:
            self.user_type = self.user_field.rel_db_type(self.conn)

    def setup(self):
        pass

    def get_models(self):
        # TODO: specify apps/excludes in settings and in CLI
        return [
            model
            for model in apps.get_models(include_auto_created=True)
            if not issubclass(model, HistoricalModel)
            and model._meta.app_label not in ("sessions", "contenttypes")
        ]

    def historical_model(self, model):
        type_name = "%sHistory" % model.__name__
        try:
            return apps.get_model("history", type_name)
        except LookupError:
            pass
        model_attrs = {
            "__module__": "history.models",
            "object": models.ForeignKey(
                model,
                db_constraint=False,
                related_name=conf.RELATED_NAME,
                on_delete=models.DO_NOTHING,
            ),
            conf.USER_FIELD: self.user_field.clone(),
        }
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

    def execute(self, sql, params=None, cursor=None, fetch=False):
        if cursor:
            cursor.execute(sql, params)
            if fetch:
                return cursor.fetchall()
        else:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, params)
                if fetch:
                    return cursor.fetchall()

    def set_user(self, user_id):
        raise NotImplementedError()

    def get_user(self):
        raise NotImplementedError()

    def clear_user(self):
        self.set_user(None)

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
        table_name = split_identifier(model._meta.db_table)[1]
        return truncate_name(
            "{}_{}_{}".format(prefix, table_name, trigger_type.name.lower())
        )

    def create_schema(self):
        raise NotImplementedError()

    def drop_schema(self):
        raise NotImplementedError()

    def create_history_table(self, model):
        history_model = self.historical_model(model)
        with self.conn.schema_editor() as schema:
            schema.create_model(history_model)

    def drop_history_table(self, model):
        history_model = self.historical_model(model)
        with self.conn.schema_editor() as schema:
            schema.delete_model(history_model)

    def create_trigger(self, model, trigger_type):
        raise NotImplementedError()

    def drop_trigger(self, model, trigger_type):
        raise NotImplementedError()
