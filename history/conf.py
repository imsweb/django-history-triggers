from django.conf import settings

# A list of path prefixes the history middleware should ignore.
MIDDLEWARE_IGNORE = getattr(settings, "HISTORY_MIDDLEWARE_IGNORE", [])

# The function to get the current user ID from a request.
REQUEST_USER = getattr(settings, "HISTORY_REQUEST_USER", "history.get_request_user")

# Whether to register the ObjectHistory admin by default.
ADMIN_ENABLED = getattr(settings, "HISTORY_ADMIN_ENABLED", True)
