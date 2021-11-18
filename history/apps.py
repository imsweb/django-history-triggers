from django.apps import AppConfig
from django.db.backends.base.base import NO_DB_ALIAS
from django.db.backends.signals import connection_created


class HistoryConfig(AppConfig):
    name = "history"

    def ready(self):
        connection_created.connect(self.setup_connection, dispatch_uid="history")

    def setup_connection(self, sender, **kwargs):
        conn = kwargs["connection"]
        if conn.alias == NO_DB_ALIAS:
            return
        from .backends import get_backend

        backend = get_backend(conn.alias)
        backend.setup()
