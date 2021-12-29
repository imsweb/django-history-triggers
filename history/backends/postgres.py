from django.contrib.contenttypes.models import ContentType

from history import get_history_model

from .base import HistoryBackend, HistorySession

TRIGGER_FUNCTION_SQL = """
    CREATE OR REPLACE FUNCTION history_record() RETURNS trigger AS $BODY$
    DECLARE
        _ctid integer := TG_ARGV[0]::integer;
        _pk_name text := TG_ARGV[1];
        _old jsonb := to_jsonb(OLD);
        _new jsonb := to_jsonb(NEW);
        _changes jsonb;
    BEGIN
        IF (TG_OP = 'UPDATE') THEN
            SELECT
                jsonb_object_agg(
                    coalesce(n.key, o.key),
                    jsonb_build_array(o.value, n.value)
                ) INTO _changes
            FROM
                jsonb_each(_old) o
                FULL OUTER JOIN jsonb_each(_new) n ON n.key = o.key
            WHERE
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
            coalesce(_new->>_pk_name, _old->>_pk_name)::{obj_type},
            coalesce(_new, _old),
            _changes,
            {session_values}
        );

        RETURN NULL;
    END; $BODY$
    LANGUAGE 'plpgsql' VOLATILE;
"""


class PostgresHistorySession(HistorySession):
    def start(self):
        parts = []
        params = []
        for name, value in self.fields.items():
            parts.append("set_config('history.{field}', %s, false)".format(field=name))
            params.append(str(value))
        sql = "SELECT {};".format(", ".join(parts))
        self.backend.execute(sql, params)

    def stop(self):
        parts = []
        for name, value in self.fields.items():
            parts.append("set_config('history.{field}', '', false)".format(field=name))
        self.backend.execute("SELECT {};".format(", ".join(parts)))


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
        self.execute("DROP FUNCTION IF EXISTS history_record();")

    def clear(self):
        HistoryModel = get_history_model()
        self.execute("TRUNCATE {table};".format(table=HistoryModel._meta.db_table))

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
