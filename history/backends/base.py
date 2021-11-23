from django.apps import apps
from django.db.backends.utils import split_identifier, truncate_name

from history.models import AbstractObjectHistory


class HistorySession:
    def __init__(self, backend, user_id):
        self.backend = backend
        self.user_id = user_id

    def start(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def __enter__(self):
        return self.start()

    def __exit__(self, *exc_details):
        self.stop()


class HistoryBackend:
    session_class = HistorySession

    def __init__(self, connection):
        self.conn = connection

    def install(self):
        pass

    def remove(self):
        pass

    def get_models(self):
        # TODO: specify apps/excludes in settings and in CLI
        return [
            model
            for model in apps.get_models(include_auto_created=True)
            if not issubclass(model, AbstractObjectHistory)
            and model._meta.app_label not in ("admin", "sessions", "contenttypes")
        ]

    def execute(self, sql, params=None, fetch=False):
        with self.conn.cursor() as cursor:
            if isinstance(sql, str):
                cursor.execute(sql, params)
            else:
                for stmt in sql:
                    cursor.execute(stmt, params)
            if fetch:
                return cursor.fetchall()

    def session(self, user_id):
        return self.session_class(self, user_id)

    def trigger_name(self, model, trigger_type, prefix="tr"):
        table_name = split_identifier(model._meta.db_table)[1]
        return truncate_name(
            "{}_{}_{}".format(prefix, table_name, trigger_type.name.lower())
        )

    def create_trigger(self, model, trigger_type):
        raise NotImplementedError()

    def drop_trigger(self, model, trigger_type):
        raise NotImplementedError()
