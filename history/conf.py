from django.conf import settings

# Schema to create for history tables (if supported).
SCHEMA_NAME = getattr(settings, "HISTORY_SCHEMA", "history")

# Prefix and suffix for the history table names.
TABLE_PREFIX = getattr(settings, "HISTORY_TABLE_PREFIX", "")
TABLE_SUFFIX = getattr(settings, "HISTORY_TABLE_SUFFIX", "")

# The related_name to use for the ForeignKey from historical model to actual model.
RELATED_NAME = getattr(settings, "HISTORY_RELATED_NAME", "history")

# Session variable to store current user. In SQLite, this is defined as a connection
# function, i.e. get_history_user().
USER_VARIABLE = getattr(settings, "HISTORY_USER_VARIABLE", "history.user")

# Model field and field name for the user field on history tables.
USER_FIELD = getattr(settings, "HISTORY_USER_FIELD", "user")
USER_MODEL = getattr(
    settings, "HISTORY_USER_MODEL", "django.contrib.auth.get_user_model"
)

# A list of path prefixes the history middleware should ignore.
MIDDLEWARE_IGNORE = getattr(settings, "HISTORY_MIDDLEWARE_IGNORE", [])

# The function to get the current user ID from a request.
REQUEST_USER = getattr(
    settings, "HISTORY_REQUEST_USER", "history.utils.get_request_user"
)
