from django.db.utils import ProgrammingError

from history import conf
from history.models import TriggerType

from .base import HistoryBackend


class SQLiteHistoryBackend(HistoryBackend):
    supports_schemas = False

    def set_user(self, user_id):
        def current_user():
            return user_id

        self.conn.connection.create_function(conf.USER_TEMP_TABLE, 0, current_user)

    def get_user(self):
        return self.execute(
            "SELECT %(func)s()" % {"func": conf.USER_TEMP_TABLE}, fetch=True
        )[0][0]

    def clear_user(self):
        def no_user():
            raise ProgrammingError("No {} set.".format(conf.USER_TEMP_TABLE))

        self.conn.connection.create_function(conf.USER_TEMP_TABLE, 0, no_user)

    def _json_object(self, model, alias):
        """
        Returns an SQL fragment that builds a JSON object from all database fields
        defined on `model`.
        """
        parts = []
        for f in model._meta.get_fields(include_parents=False):
            if f.many_to_many or not f.concrete:
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
                            %(values)s
                        )
                    )
                WHERE oldval IS NOT newval))
        """ % {
            "values": ", ".join(parts)
        }

    def create_schema(self):
        pass

    def drop_schema(self):
        for model in self.get_models():
            for trigger_type in TriggerType:
                self.drop_trigger(model, trigger_type)
            self.drop_history_table(model)

    def create_trigger(self, model, trigger_type):
        self.drop_trigger(model, trigger_type)
        self.execute(
            """
            CREATE TRIGGER %(trigger_name)s AFTER %(action)s ON %(table)s BEGIN
                INSERT INTO %(history_table)s (
                    %(pk_name)s,
                    snapshot,
                    changes,
                    %(user_field)s,
                    event_date,
                    event_type
                )
                VALUES (
                    %(pk_ref)s.%(pk_name)s,
                    %(snapshot)s,
                    %(changes)s,
                    %(user_table)s(),
                    CURRENT_TIMESTAMP,
                    '%(type)s'
                );
            END;
            """
            % {
                "trigger_name": self.trigger_name(model, trigger_type),
                "action": trigger_type.name,
                "table": model._meta.db_table,
                "history_table": self.history_table_name(model._meta.db_table),
                "pk_name": model._meta.pk.column,
                "pk_ref": trigger_type.snapshot,
                "user_field": conf.USER_FIELD,
                "user_table": conf.USER_TEMP_TABLE,
                "snapshot": self._json_object(model, trigger_type.snapshot),
                "changes": self._json_changes(model)
                if trigger_type.changes
                else "NULL",
                "type": trigger_type.value,
            }
        )
        return self.trigger_name(model, trigger_type)

    def drop_trigger(self, model, trigger_type):
        self.execute(
            "DROP TRIGGER IF EXISTS %(trigger_name)s;"
            % {
                "trigger_name": self.trigger_name(model, trigger_type),
            }
        )
