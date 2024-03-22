from django.contrib.contenttypes.models import ContentType
from django.db import models

from history import conf, get_history_model

from .base import HistoryBackend, HistorySession


def column(field, ref):
    if isinstance(field, models.BinaryField):
        # Match the way Postgres converts bytea to a JSON string.
        return "'\\x' || nullif(hex({}.\"{}\"), '')".format(ref, field.column)
    elif isinstance(field, models.JSONField):
        # Explicitly call json so SQLite won't force it to a string.
        return 'json({}."{}")'.format(ref, field.column)
    else:
        return '{}."{}"'.format(ref, field.column)


class SQLiteHistorySession(HistorySession):
    def start(self):
        # This is to bind "name" since it's in a loop.
        def getter(name):
            return lambda: self.fields.get(name)

        # Create a function for every session field, named "history_{column}".
        for field in self.backend.session_fields():
            self.backend.conn.connection.create_function(
                "history_{}".format(field.column), 0, getter(field.name)
            )

        # History recording is enabled by default.
        self.backend.conn.connection.create_function(
            "_history_enabled", 0, lambda: True
        )

    def stop(self):
        for field in self.backend.session_fields():
            self.backend.conn.connection.create_function(
                "history_{}".format(field.column), 0, lambda: None
            )

    def pause(self):
        self.backend.conn.connection.create_function(
            "_history_enabled", 0, lambda: False
        )

    def resume(self):
        self.backend.conn.connection.create_function(
            "_history_enabled", 0, lambda: True
        )


class SQLiteHistoryBackend(HistoryBackend):
    session_class = SQLiteHistorySession

    def _json_object(self, fields, ref):
        parts = []
        for f in fields:
            parts.append("'{}'".format(f.column))
            parts.append(column(f, ref))
        return "json_object({})".format(", ".join(parts))

    def _json_snapshot(self, fields, trigger_type):
        """
        Returns an SQL fragment that builds a JSON object from the specified model
        fields.
        """
        if not conf.SNAPSHOTS or not trigger_type.snapshot:
            return "NULL"
        return self._json_object(fields, "NEW")

    def _json_changes(self, fields, trigger_type):
        """
        Returns a sub-select that generates a JSON object of changed fields between OLD
        and NEW, in the format:

            `{"field": [oldval, newval]}`
        """
        if not trigger_type.changes:
            return "NULL"
        return """
            (
                SELECT
                    json_group_object(
                        coalesce(n.key, o.key),
                        json_array(o.value, n.value)
                    ) AS changes
                FROM
                    json_each({oldvals}) o,
                    json_each({newvals}) n
                WHERE
                    n.key = o.key AND n.value IS NOT o.value
            )
        """.format(
            oldvals=self._json_object(fields, "OLD"),
            newvals=self._json_object(fields, "NEW"),
        )

    def create_trigger(self, model, trigger_type):
        HistoryModel = get_history_model()
        ct = ContentType.objects.db_manager(self.alias).get_for_model(model)
        tr_name = self.trigger_name(model, trigger_type)
        session_cols = []
        session_values = []
        for field in self.session_fields():
            session_cols.append('"' + field.column + '"')
            session_values.append("history_{}()".format(field.column))
        self.drop_trigger(model, trigger_type)
        fields = list(self.model_fields(model, trigger_type))
        if not fields:
            return tr_name, []
        self.execute(
            """
            CREATE TRIGGER {trigger_name} AFTER {action} ON {table} BEGIN
                INSERT INTO {history_table} (
                    change_type,
                    content_type_id,
                    object_id,
                    snapshot,
                    changes,
                    {session_cols}
                )
                SELECT
                    '{change_type}',
                    {ctid},
                    {pk_ref}.{pk_col},
                    {snapshot},
                    {changes},
                    {session_values}
                WHERE _history_enabled();
            END;
            """.format(
                trigger_name=tr_name,
                action=trigger_type.name,
                table=model._meta.db_table,
                history_table=HistoryModel._meta.db_table,
                change_type=trigger_type.value,
                ctid=ct.pk,
                pk_ref=trigger_type.pk_alias,
                pk_col=model._meta.pk.column,
                snapshot=self._json_snapshot(fields, trigger_type),
                changes=self._json_changes(fields, trigger_type),
                session_cols=", ".join(session_cols),
                session_values=", ".join(session_values),
            )
        )
        return tr_name, [f.column for f in fields]

    def drop_trigger(self, model, trigger_type):
        self.execute(
            "DROP TRIGGER IF EXISTS {trigger_name};".format(
                trigger_name=self.trigger_name(model, trigger_type),
            )
        )
