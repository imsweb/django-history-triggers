from django.conf import settings

SCHEMA_NAME = getattr(settings, "HISTORY_SCHEMA", "history")
TABLE_PREFIX = getattr(settings, "HISTORY_TABLE_PREFIX", "")
TABLE_SUFFIX = getattr(settings, "HISTORY_TABLE_SUFFIX", "")
USER_TEMP_TABLE = getattr(settings, "HISTORY_USER_TEMP_TABLE", "history_user")
USER_FIELD = getattr(settings, "HISTORY_USER_FIELD", "user_id")
USER_TYPE = getattr(settings, "HISTORY_USER_TYPE", "integer")
USER_LOOKUP = getattr(settings, "HISTORY_USER_LOOKUP", "history.utils.get_user")

# Controls which user attribute gets associated with history entries.
REQUEST_USER_FIELD = getattr(settings, "HISTORY_REQUEST_USER_FIELD", "user")
REQUEST_USER_ATTRIBUTE = getattr(settings, "HISTORY_REQUEST_USER_ATTRIBUTE", "pk")

# A list of path prefixes the history middleware should ignore.
MIDDLEWARE_IGNORE = getattr(settings, "HISTORY_MIDDLEWARE_IGNORE", [])
