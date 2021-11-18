from django.conf import settings

SCHEMA_NAME = getattr(settings, "HISTORY_SCHEMA", "history")
TABLE_PREFIX = getattr(settings, "HISTORY_TABLE_PREFIX", "")
TABLE_SUFFIX = getattr(settings, "HISTORY_TABLE_SUFFIX", "")
USER_TEMP_TABLE = getattr(settings, "HISTORY_USER_TEMP_TABLE", "history_user")
USER_FUNCION = getattr(settings, "HISTORY_USER_FUNCTION", "get_history_user")
USER_FIELD = getattr(settings, "HISTORY_USER_FIELD", "user_id")
USER_TYPE = getattr(settings, "HISTORY_USER_TYPE", "integer")
USER_NULLABLE = getattr(settings, "HISTORY_USER_NULLABLE", True)
USER_LOOKUP = getattr(settings, "HISTORY_USER_LOOKUP", "history.utils.get_user")

# A list of path prefixes the history middleware should ignore.
MIDDLEWARE_IGNORE = getattr(settings, "HISTORY_MIDDLEWARE_IGNORE", [])
REQUEST_USER = getattr(settings, "HISTORY_REQUEST_USER", "history.utils.request_user")
