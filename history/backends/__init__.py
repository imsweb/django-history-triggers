from django.conf import settings
from django.db import DEFAULT_DB_ALIAS

backend_cache = {}


def get_backend(alias=DEFAULT_DB_ALIAS, cls=None, cache=True):
    if cache and alias in backend_cache:
        return backend_cache[alias]

    if cls:
        backend = cls(alias)
    else:
        engine = settings.DATABASES[alias]["ENGINE"].split(".")[-1]
        if engine in ("postgresql", "postgis"):
            from .postgres import PostgresHistoryBackend

            backend = PostgresHistoryBackend(alias)
        elif engine == "sqlite3":
            from .sqlite import SQLiteHistoryBackend

            backend = SQLiteHistoryBackend(alias)
        else:
            raise ValueError("Unsupported database engine: {}".format(engine))

    if cache:
        backend_cache[alias] = backend

    return backend
