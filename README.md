# django-history-triggers

`django-history-triggers` is a Django application for installing database triggers
that automatically record inserts, updates, and deletes to model tables.


## Requirements

* Django 3.0+
* PostgreSQL or SQLite database


## Installation

`pip install django-history-triggers`


## Quick Start

1. Add `history` to your INSTALLED_APPS setting and migrate your database.
2. Add `history.middleware.HistoryMiddleware` to the end of your `MIDDLEWARE` setting.
3. Run `manage.py triggers enable` to install the trigger functions, or
   `manage.py triggers disable` to uninstall them. Neither will clear existing history
   data -- add a `--clear` option to do that.


## Settings

* `HISTORY_MODEL` (default: `"history.ObjectHistory"`)
* `HISTORY_IGNORE_APPS` (default: `["admin", "contenttypes", "sessions"]`)
* `HISTORY_MIDDLEWARE_IGNORE` (default: `[]`)
* `HISTORY_REQUEST_CONTEXT` (default: `"history.get_request_context"`)
* `HISTORY_ADMIN_ENABLED` (default: `True`)


## History Sessions

History is recorded within "sessions" that you can manage manually, either outside of
a web request context, or in place of or in addition to the included middleware. The
easiest way to manage a history session is via a context manager:

```python
from history import get_backend

def api_view(request):
    # You can pass extra fields to be stored for all history within a session.
    with get_backend().session(user=request.user, path=request.path):
        # All history inside here will have the same session_id and session_date.
        ...
```


## Custom History Model

The default `history.ObjectHistory` model is swappable by changing the `HISTORY_MODEL`
setting. If you need to define your own object history model (usually for tracking
custom fields or non-standard user info), be sure to inherit from
`history.models.AbstractObjectHistory`. If at all possible, do this early on to avoid
problems with migrations when changing `HISTORY_MODEL` after the initial migration.
