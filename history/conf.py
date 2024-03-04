from django.conf import settings

SCHEMA_NAME = getattr(settings, "HISTORY_SCHEMA", "history")
USER_TEMP_TABLE = getattr(settings, "HISTORY_USER_TEMP_TABLE", "history_user")
USER_FIELD = getattr(settings, "HISTORY_USER_FIELD", "user_id")
USER_TYPE = getattr(settings, "HISTORY_USER_TYPE", "integer")
DEFAULT_USER = getattr(settings, "HISTORY_DEFAULT_USER", 0)
DEFAULT_USER_ERROR = getattr(settings, "HISTORY_DEFAULT_USER_ERROR", False)

# The database role that should own the history tables and triggers.
DB_ROLE = getattr(settings, "HISTORY_DB_ROLE", settings.DATABASES["default"]["USER"])

# Base tables which do not get history attached.
IGNORED_TABLES = getattr(settings, "HISTORY_IGNORED_TABLES", [])
IGNORED_PREFIXES = getattr(
    settings, "HISTORY_IGNORED_PREFIXES", ["django_", "auth_", "south_"]
)

# Columns which should not be tracked in history tables.
IGNORED_TYPES = getattr(settings, "HISTORY_IGNORED_TYPES", ["bytea"])
IGNORED_COLUMNS = getattr(settings, "HISTORY_IGNORED_COLUMNS", [])

# Controls the column type for the date_modified field on history tables.
USE_TIMEZONES = getattr(settings, "HISTORY_USE_TIMEZONES", True)

# If set to True, old_value/new_value will be JSON records instead of tracking
# individual field updates.
USE_JSON = getattr(settings, "HISTORY_JSON", False)

# Controls which user attribute gets associated with history entries.
REQUEST_USER_FIELD = getattr(settings, "HISTORY_REQUEST_USER_FIELD", "user")
REQUEST_USER_ATTRIBUTE = getattr(settings, "HISTORY_REQUEST_USER_ATTRIBUTE", "pk")

# A list of path prefixes the history middleware should ignore.
MIDDLEWARE_IGNORE = getattr(
    settings,
    "HISTORY_MIDDLEWARE_IGNORE",
    [settings.STATIC_URL, settings.MEDIA_URL],
)
