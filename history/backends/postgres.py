from django.contrib.contenttypes.models import ContentType

from history import conf, get_history_model

from .base import HistoryBackend, HistorySession

TRIGGER_FUNCTION_SQL = """
    CREATE OR REPLACE FUNCTION history_record() RETURNS trigger AS $BODY$
    DECLARE
        _ctid integer := TG_ARGV[0]::integer;
        _pk_name text := TG_ARGV[1];
        _record_snap boolean := TG_ARGV[2]::boolean;
        _fields text[] := TG_ARGV[3:];
        _old jsonb := to_jsonb(OLD);
        _new jsonb := to_jsonb(NEW);
        _snapshot jsonb;
        _changes jsonb;
        _paused boolean;
    BEGIN
        IF current_setting('history.__paused', true) IS NOT DISTINCT FROM 'true' THEN
            RETURN NULL;
        END IF;

        IF _record_snap THEN
            SELECT jsonb_object_agg(key, value) INTO _snapshot
            FROM jsonb_each(_new)
            WHERE key = ANY(_fields);
        END IF;

        IF (TG_OP = 'UPDATE') THEN
            SELECT
                jsonb_object_agg(
                    coalesce(n.key, o.key),
                    jsonb_build_array(o.value, n.value)
                ) INTO _changes
            FROM
                jsonb_each(_old) o,
                jsonb_each(_new) n
            WHERE
                n.key = o.key AND
                n.key = ANY(_fields) AND
                n.value IS DISTINCT FROM o.value;
        END IF;

        INSERT INTO {table} (
            change_type,
            content_type_id,
            object_id,
            snapshot,
            changes,
            {session_cols}
        )
        VALUES (
            substr(TG_OP, 1, 1),
            _ctid,
            coalesce(_old->>_pk_name, _new->>_pk_name)::{obj_type},
            _snapshot,
            _changes,
            {session_values}
        );

        RETURN NULL;
    END; $BODY$
    LANGUAGE 'plpgsql' VOLATILE;
"""


class PostgresHistorySession(HistorySession):
    def start_sql(self):
        parts = []
        params = []
        for name, value in self.fields.items():
            parts.append("set_config('history.{field}', %s, false)".format(field=name))
            params.append(str(value))
        return "SELECT {};".format(", ".join(parts)), params

    def stop_sql(self):
        parts = []
        for name, value in self.fields.items():
            parts.append("set_config('history.{field}', '', false)".format(field=name))
        return "SELECT {};".format(", ".join(parts)), []

    def pause(self):
        self.backend.execute("SELECT set_config('history.__paused', 'true', false)")

    def resume(self):
        self.backend.execute("SELECT set_config('history.__paused', NULL, false)")


class PostgresHistoryBackend(HistoryBackend):
    session_class = PostgresHistorySession

    def install(self):
        HistoryModel = get_history_model()
        obj_type = HistoryModel._meta.get_field("object_id").db_type(self.conn)
        session_cols = []
        session_values = []
        for field in self.session_fields():
            session_cols.append(field.column)
            session_values.append(
                "nullif(current_setting('history.{field}', true), '')::{type}".format(
                    field=field.name,
                    type=field.rel_db_type(self.conn),
                )
            )
        self.execute(
            TRIGGER_FUNCTION_SQL.format(
                table=HistoryModel._meta.db_table,
                obj_type=obj_type,
                session_cols=", ".join(session_cols),
                session_values=", ".join(session_values),
            )
        )

    def remove(self):
        self.execute("DROP FUNCTION IF EXISTS history_record() CASCADE;")

    def clear(self):
        HistoryModel = get_history_model()
        self.execute("TRUNCATE {table};".format(table=HistoryModel._meta.db_table))

    def create_trigger(self, model, trigger_type):
        ct = ContentType.objects.db_manager(self.alias).get_for_model(model)
        tr_name = self.trigger_name(model, trigger_type)
        self.execute(
            "DROP TRIGGER IF EXISTS {tr_name} ON {table};".format(
                tr_name=tr_name,
                table=model._meta.db_table,
            )
        )
        field_names = [f.column for f in self.model_fields(model, trigger_type)]
        if not field_names:
            return tr_name, []
        self.execute(
            """
                CREATE TRIGGER {tr_name} AFTER {trans_type} ON {table}
                FOR EACH ROW EXECUTE PROCEDURE
                history_record({ctid}, '{pk_col}', {snapshots}{field_list});
            """.format(
                tr_name=tr_name,
                trans_type=trigger_type.name.upper(),
                table=model._meta.db_table,
                ctid=ct.pk,
                pk_col=model._meta.pk.column,
                snapshots=int(conf.SNAPSHOTS and trigger_type.snapshot),
                field_list=", '" + "', '".join(field_names) + "'",
            )
        )
        return tr_name, field_names

    def drop_trigger(self, model, trigger_type):
        self.execute(
            "DROP TRIGGER IF EXISTS {tr_name} ON {table};".format(
                tr_name=self.trigger_name(model, trigger_type),
                table=model._meta.db_table,
            )
        )
