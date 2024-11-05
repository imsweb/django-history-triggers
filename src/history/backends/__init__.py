from asgiref.local import Local
from django.conf import settings
from django.db import DEFAULT_DB_ALIAS

backend_cache = Local()


def get_backend(alias=DEFAULT_DB_ALIAS, cls=None, cache=True):
    if cache and hasattr(backend_cache, alias):
        return getattr(backend_cache, alias)

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
        setattr(backend_cache, alias, backend)

    return backend


def session(alias=DEFAULT_DB_ALIAS, **context):
    return get_backend(alias).session(**context)
