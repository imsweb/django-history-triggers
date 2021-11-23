import uuid

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from history import get_history_model

from .base import HistoryBackend, HistorySession


class SQLiteHistorySession(HistorySession):
    def start(self):
        self.session_id = uuid.uuid4()
        self.session_date = timezone.now()
        # Make sure we have an open connection, and create the history functions.
        self.backend.conn.ensure_connection()
        self.backend.conn.connection.create_function(
            "history_session_id", 0, lambda: str(self.session_id)
        )
        self.backend.conn.connection.create_function(
            "history_session_date", 0, lambda: self.session_date.isoformat()
        )
        self.backend.conn.connection.create_function(
            "history_session_user", 0, lambda: self.user_id
        )

    def stop(self):
        self.backend.conn.ensure_connection()
        self.backend.conn.connection.create_function(
            "history_session_id", 0, lambda: None
        )
        self.backend.conn.connection.create_function(
            "history_session_date", 0, lambda: None
        )
        self.backend.conn.connection.create_function(
            "history_session_user", 0, lambda: None
        )


class SQLiteHistoryBackend(HistoryBackend):
    session_class = SQLiteHistorySession

    def _json_object(self, model, alias):
        """
        Returns an SQL fragment that builds a JSON object from all database fields
        defined on `model`.
        """
        parts = []
        for f in model._meta.get_fields(include_parents=False):
            if f.many_to_many or not f.concrete:
                continue
            if isinstance(f, models.BinaryField):
                # TODO: fix this
                continue
            parts.append("'{}'".format(f.column))
            parts.append("{}.{}".format(alias, self.conn.ops.quote_name(f.column)))
        return "json_object({})".format(", ".join(parts))

    def _json_changes(self, model):
        """
        Returns a sub-select that generates a JSON object of changed fields between OLD
        and NEW, in the format:

            `{"field": [oldval, newval]}`
        """
        parts = []
        for f in model._meta.get_fields(include_parents=False):
            if f.many_to_many or not f.concrete:
                continue
            if isinstance(f, models.BinaryField):
                # TODO: fix this
                continue
            parts.append(
                "json_array('{name}', OLD.{col}, NEW.{col})".format(
                    name=f.column,
                    col=self.conn.ops.quote_name(f.column),
                )
            )
        # Largely taken from:
        # https://blog.budgetwithbuckets.com/2018/08/27/sqlite-changelog.html
        return """
            (SELECT
                json_group_object(col, json_array(oldval, newval)) AS changes
            FROM
                (SELECT
                    json_extract(value, '$[0]') as col,
                    json_extract(value, '$[1]') as oldval,
                    json_extract(value, '$[2]') as newval
                FROM
                    json_each(
                        json_array(
                            {values}
                        )
                    )
                WHERE oldval IS NOT newval))
        """.format(
            values=", ".join(parts)
        )

    def create_trigger(self, model, trigger_type):
        HistoryModel = get_history_model()
        user_col = HistoryModel._meta.get_field(HistoryModel.USER_FIELD).column
        ct = ContentType.objects.get_for_model(model)
        tr_name = self.trigger_name(model, trigger_type)
        self.drop_trigger(model, trigger_type)
        self.execute(
            """
            CREATE TRIGGER {trigger_name} AFTER {action} ON {table} BEGIN
                INSERT INTO {history_table} (
                    session_id,
                    session_date,
                    {user_col},
                    change_type,
                    content_type_id,
                    object_id,
                    snapshot,
                    changes
                )
                VALUES (
                    history_session_id(),
                    history_session_date(),
                    history_session_user(),
                    '{change_type}',
                    {ctid},
                    {pk_ref}.{pk_col},
                    {snapshot},
                    {changes}
                );
            END;
            """.format(
                trigger_name=tr_name,
                action=trigger_type.name,
                table=model._meta.db_table,
                history_table=HistoryModel._meta.db_table,
                user_col=user_col,
                change_type=trigger_type.value,
                ctid=ct.pk,
                pk_ref=trigger_type.snapshot,
                pk_col=model._meta.pk.column,
                snapshot=self._json_object(model, trigger_type.snapshot),
                changes=self._json_changes(model) if trigger_type.changes else "NULL",
            )
        )
        return tr_name

    def drop_trigger(self, model, trigger_type):
        self.execute(
            "DROP TRIGGER IF EXISTS {trigger_name};".format(
                trigger_name=self.trigger_name(model, trigger_type),
            )
        )
