# django-history-triggers

`django-history-triggers` is a Django application for installing database triggers
that automatically record inserts, updates, and deletes to model tables.


## Requirements

* Django 3.2+
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
* `HISTORY_FILTER` (default: `"history.utils.default_filter"`)
* `HISTORY_REQUEST_CONTEXT` (default: `"history.utils.get_request_context"`)
* `HISTORY_ADMIN_ENABLED` (default: `True`)
* `HISTORY_INCLUDE_UNMANAGED` (default: `True`)


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

Starting in 3.4.2, you can also "pause" history recording within a session:

```python
 with get_backend().session() as session:
     Model.objects.create(name="This history is recorded")
     with session.paused():
        Model.objects.create(name="This history is NOT recorded")
     Model.objects.create(name="This history is also recorded")
```


## Custom History Model

The default `history.ObjectHistory` model is swappable by changing the `HISTORY_MODEL`
setting. If you need to define your own object history model (usually for tracking
custom fields or non-standard user info), be sure to inherit from
`history.models.AbstractObjectHistory`. If at all possible, do this early on to avoid
problems with migrations when changing `HISTORY_MODEL` after the initial migration.


## Filtering History

The `HISTORY_FILTER` setting allows you to fully customize which fields (or even whole
models) should be included in or excluded from history. It is implemented as a callable
that takes three parameters:

* The `django.db.models.Model` class being filtered
* The `django.db.models.fields.Field` instance in question
* The `history.models.TriggerType` being created

The filter should return `True` if the field should be included, and `False` if it
should be excluded. The default implementation (`history.utils.default_filter`) simply
includes any field except `BinaryField`s:

```python
def default_filter(model, field, trigger_type):
    return not isinstance(field, models.BinaryField)
```

Returning `False` for all fields of any given model has the effect of not tracking
history for that model:

```python
def filter_sensitive(model, field, trigger_type):
    return not issubclass(model, SensitiveDataModel)
```

Similarly, if you (for example) only wanted to record history for UPDATE statements:

```python
def updates_only(model, field, trigger_type):
    return trigger_type == TriggerType.UPDATE
```


## Management Commands

By default `django-history-triggers` does not override any of Django's management
commands that may perform database operations, such as `loaddata` or `migrate`. If you
need to run these commands with history triggers enabled, you can include the following
apps in your `INSTALLED_APPS` setting:

* `history.contrib.loaddata`
* `history.contrib.migrate`

The `HISTORY_LOADDATA_CONTEXT` and `HISTORY_MIGRATE_CONTEXT` settings control the
history session context for the respective command, for example:

```python
HISTORY_MIGRATE_CONTEXT = {"user": "system"}
```
