from django.contrib.contenttypes.models import ContentType

from history import get_history_model

from .base import HistoryBackend, HistorySession

START_FUNCTION_SQL = """
    CREATE OR REPLACE FUNCTION history_start(user_id text) RETURNS uuid AS $BODY$
    DECLARE
        _session_id uuid := gen_random_uuid();
    BEGIN
        PERFORM
            set_config('history.user_id', user_id, false),
            set_config('history.session_id', _session_id::text, false),
            set_config('history.session_date', now()::text, false);
        RETURN _session_id;
    END; $BODY$
    LANGUAGE 'plpgsql' VOLATILE;
"""

STOP_FUNCTION_SQL = """
    CREATE OR REPLACE FUNCTION history_stop() RETURNS uuid AS $BODY$
    DECLARE
        _session_id uuid;
    BEGIN
        SELECT nullif(current_setting('history.session_id', true), '')::uuid
            INTO _session_id;
        PERFORM
            set_config('history.user_id', '', false),
            set_config('history.session_id', '', false),
            set_config('history.session_date', '', false);
        RETURN _session_id;
    END; $BODY$
    LANGUAGE 'plpgsql' VOLATILE;
"""

TRIGGER_FUNCTION_SQL = """
    CREATE OR REPLACE FUNCTION history_record() RETURNS trigger AS $BODY$
    DECLARE
        _ctid integer := TG_ARGV[0]::integer;
        _pk_name text := TG_ARGV[1];
        _old jsonb := to_jsonb(OLD);
        _new jsonb := to_jsonb(NEW);
        _user_id text := current_setting('history.user_id', true);
        _session_id uuid := current_setting('history.session_id', true)::uuid;
        _session_date timestamptz :=
            current_setting('history.session_date', true)::timestamptz;
        _changes jsonb;
    BEGIN
        IF (TG_OP = 'UPDATE') THEN
            SELECT
                jsonb_object_agg(
                    coalesce(o.key, n.key),
                    jsonb_build_array(o.value, n.value)
                ) INTO _changes
            FROM
                jsonb_each(_old) o
                FULL OUTER JOIN jsonb_each(_new) n ON n.key = o.key
            WHERE
                n.value IS DISTINCT FROM o.value;
        END IF;

        INSERT INTO {table} (
            session_id,
            session_date,
            change_type,
            content_type_id,
            object_id,
            snapshot,
            changes,
            {user_col}
        )
        VALUES (
            _session_id,
            _session_date,
            substr(TG_OP, 1, 1),
            _ctid,
            coalesce(_old->>_pk_name, _new->>_pk_name)::{obj_type},
            to_jsonb(coalesce(NEW, OLD)),
            _changes,
            _user_id::{user_type}
        );

        RETURN coalesce(NEW, OLD);
    END; $BODY$
    LANGUAGE 'plpgsql' VOLATILE;
"""


class PostgresHistorySession(HistorySession):
    def start(self):
        self.backend.execute("SELECT history_start(%s);", (str(self.user_id),))

    def stop(self):
        self.backend.execute("SELECT history_stop();")


class PostgresHistoryBackend(HistoryBackend):
    session_class = PostgresHistorySession

    def install(self):
        HistoryModel = get_history_model()
        user_field = HistoryModel._meta.get_field(HistoryModel.USER_FIELD)
        obj_type = HistoryModel._meta.get_field("object_id").db_type(self.conn)
        self.execute(
            [
                TRIGGER_FUNCTION_SQL.format(
                    table=HistoryModel._meta.db_table,
                    user_col=user_field.column,
                    user_type=user_field.rel_db_type(self.conn),
                    obj_type=obj_type,
                ),
                START_FUNCTION_SQL,
                STOP_FUNCTION_SQL,
            ]
        )

    def remove(self):
        self.execute(
            [
                "DROP FUNCTION IF EXISTS history_record();",
                "DROP FUNCTION IF EXISTS history_start(text);",
                "DROP FUNCTION IF EXISTS history_stop();",
            ]
        )

    def create_trigger(self, model, trigger_type):
        ct = ContentType.objects.get_for_model(model)
        tr_name = self.trigger_name(model, trigger_type)
        self.execute(
            """
            CREATE OR REPLACE TRIGGER {tr_name}
                AFTER {trans_type} ON {table}
                FOR EACH ROW EXECUTE PROCEDURE history_record({ctid}, '{pk_col}');
            """.format(
                tr_name=tr_name,
                trans_type=trigger_type.name.upper(),
                table=model._meta.db_table,
                ctid=ct.pk,
                pk_col=model._meta.pk.column,
            )
        )
        return tr_name

    def drop_trigger(self, model, trigger_type):
        self.execute(
            "DROP TRIGGER IF EXISTS {tr_name} ON {table};".format(
                tr_name=self.trigger_name(model, trigger_type),
                table=model._meta.db_table,
            )
        )
