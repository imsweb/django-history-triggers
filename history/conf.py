from django.conf import settings

IGNORE_APPS = getattr(
    settings, "HISTORY_IGNORE_APPS", ["admin", "contenttypes", "sessions"]
)

# A list of path prefixes the history middleware should ignore.
MIDDLEWARE_IGNORE = getattr(settings, "HISTORY_MIDDLEWARE_IGNORE", [])

# The function to get the current user ID from a request.
REQUEST_CONTEXT = getattr(
    settings, "HISTORY_REQUEST_CONTEXT", "history.get_request_context"
)

# Whether to register the ObjectHistory admin by default.
ADMIN_ENABLED = getattr(settings, "HISTORY_ADMIN_ENABLED", True)
