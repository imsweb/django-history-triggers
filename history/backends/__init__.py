from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, connections


def get_backend(alias=DEFAULT_DB_ALIAS):
    engine = settings.DATABASES[alias]["ENGINE"].split(".")[-1]
    if engine in ("postgresql", "postgis"):
        from .postgres import PostgresHistoryBackend

        return PostgresHistoryBackend(connections[alias])
    elif engine == "sqlite3":
        from .sqlite import SQLiteHistoryBackend

        return SQLiteHistoryBackend(connections[alias])
    raise ValueError("Unsupported database engine: {}".format(engine))
