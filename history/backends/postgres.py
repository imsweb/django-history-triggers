from history import TriggerType, conf

from .base import HistoryBackend


class PostgresHistoryBackend(HistoryBackend):
    def create_schema(self):
        self.execute("CREATE SCHEMA IF NOT EXISTS {};".format(conf.SCHEMA_NAME))

    def drop_schema(self):
        self.execute("DROP SCHEMA IF EXISTS {} CASCADE;".format(conf.SCHEMA_NAME))

    def create_trigger(self, model, trigger_type):
        self.drop_trigger(model, trigger_type)

        parts = []
        for f in model._meta.get_fields(include_parents=False):
            if f.many_to_many or not f.concrete:
                continue
            parts.append(
                """
                IF OLD.%(col)s IS DISTINCT FROM NEW.%(col)s THEN
                    _changes = _changes || jsonb_build_object(
                        '%(name)s',
                        jsonb_build_array(OLD.%(col)s, NEW.%(col)s)
                    );
                END IF;
                """
                % {
                    "name": f.column,
                    "col": self.conn.ops.quote_name(f.column),
                }
            )

        self.execute(
            """
            CREATE OR REPLACE FUNCTION %(fx_name)s() RETURNS trigger AS $BODY$
                DECLARE
                    _changes %(json_type)s := '{}'::%(json_type)s;
                BEGIN
                    %(changes)s

                    INSERT INTO %(table)s (
                        %(pk_name)s,
                        snapshot,
                        changes,
                        %(user_field)s,
                        event_date,
                        event_type
                    )
                    VALUES (
                        %(pk_ref)s.%(pk_name)s,
                        row_to_json(%(pk_ref)s),
                        _changes,
                        (SELECT %(user_field)s FROM %(user_table)s),
                        now(),
                        '%(type)s'
                    );

                    RETURN %(return)s;
                END;$BODY$
            LANGUAGE 'plpgsql' VOLATILE;
            """
            % {
                "fx_name": self.trigger_name(model, trigger_type, prefix="fx"),
                "table": self.history_table_name(model._meta.db_table),
                "pk_name": model._meta.pk.name,
                "pk_ref": trigger_type.snapshot,
                "user_field": conf.USER_FIELD,
                "user_table": conf.USER_TEMP_TABLE,
                "return": "OLD" if trigger_type == TriggerType.DELETE else "NEW",
                "json_type": self.conn.data_types["JSONField"],
                "changes": "".join(parts) if trigger_type.changes else "",
                "type": trigger_type.value,
            }
        )

        self.execute(
            """
            CREATE TRIGGER %(tr_name)s
                AFTER %(trans_type)s ON "%(table)s"
                FOR EACH ROW EXECUTE PROCEDURE %(fx_name)s();
            """
            % {
                "fx_name": self.trigger_name(model, trigger_type, prefix="fx"),
                "tr_name": self.trigger_name(model, trigger_type, prefix="tr"),
                "trans_type": trigger_type.name.upper(),
                "table": model._meta.db_table,
            }
        )

    def drop_trigger(self, model, trigger_type):
        self.execute(
            'DROP TRIGGER IF EXISTS %(tr_name)s ON "%(table)s";'
            % {
                "tr_name": self.trigger_name(model, trigger_type, prefix="tr"),
                "table": model._meta.db_table,
            }
        )
        self.execute(
            "DROP FUNCTION IF EXISTS %(fx_name)s();"
            % {
                "fx_name": self.trigger_name(model, trigger_type),
            }
        )
