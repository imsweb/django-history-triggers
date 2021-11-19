from history import conf
from history.models import TriggerType

from .base import HistoryBackend


class PostgresHistoryBackend(HistoryBackend):
    def set_user(self, user_id):
        if user_id is not None:
            user_id = str(user_id)
        self.execute(
            "SELECT set_config('{config}', %s, false);".format(
                config=conf.USER_VARIABLE,
            ),
            (user_id,),
        )

    def get_user(self):
        return self.execute(
            "SELECT nullif(current_setting('{config}', true), '')::{cast};".format(
                config=conf.USER_VARIABLE,
                cast=self.user_type,
            ),
            fetch=True,
        )[0][0]

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
                IF OLD.{col} IS DISTINCT FROM NEW.{col} THEN
                    _changes = _changes || jsonb_build_object(
                        '{name}',
                        jsonb_build_array(OLD.{col}, NEW.{col})
                    );
                END IF;
                """.format(
                    col=self.conn.ops.quote_name(f.column),
                    name=f.column,
                )
            )

        self.execute(
            """
            CREATE OR REPLACE FUNCTION {fx_name}() RETURNS trigger AS $BODY$
                DECLARE
                    _changes {json_type} := {default}::{json_type};
                BEGIN
                    {changes}

                    INSERT INTO {table} (
                        object_id,
                        snapshot,
                        changes,
                        {user_col},
                        event_date,
                        event_type
                    )
                    VALUES (
                        {pk_ref}.{pk_name},
                        row_to_json({pk_ref}),
                        _changes,
                        (SELECT nullif(current_setting('{config}', true), '')::{cast}),
                        now(),
                        '{type}'
                    );

                    RETURN {return_val};
                END;$BODY$
            LANGUAGE 'plpgsql' VOLATILE;
            """.format(
                fx_name=self.trigger_name(model, trigger_type, prefix="fx"),
                table=self.history_table_name(model._meta.db_table),
                user_col=self.user_column,
                pk_name=model._meta.pk.name,
                pk_ref=trigger_type.snapshot,
                config=conf.USER_VARIABLE,
                cast=self.user_type,
                return_val="OLD" if trigger_type == TriggerType.DELETE else "NEW",
                json_type=self.conn.data_types["JSONField"],
                default="'{}'" if trigger_type.changes else "NULL",
                changes="".join(parts) if trigger_type.changes else "",
                type=trigger_type.value,
            )
        )

        self.execute(
            """
            CREATE TRIGGER {tr_name}
                AFTER {trans_type} ON {table}
                FOR EACH ROW EXECUTE PROCEDURE {fx_name}();
            """.format(
                fx_name=self.trigger_name(model, trigger_type, prefix="fx"),
                tr_name=self.trigger_name(model, trigger_type, prefix="tr"),
                trans_type=trigger_type.name.upper(),
                table=model._meta.db_table,
            )
        )

        return self.trigger_name(model, trigger_type, prefix="tr")

    def drop_trigger(self, model, trigger_type):
        self.execute(
            "DROP TRIGGER IF EXISTS {tr_name} ON {table};".format(
                tr_name=self.trigger_name(model, trigger_type, prefix="tr"),
                table=model._meta.db_table,
            )
        )
        self.execute(
            "DROP FUNCTION IF EXISTS {fx_name}();".format(
                fx_name=self.trigger_name(model, trigger_type, prefix="fx"),
            )
        )
