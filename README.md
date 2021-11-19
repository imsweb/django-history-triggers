Requirements
============

* Django 3.0+
* PostgreSQL or SQLite database


Using Django History Triggers
=============================

1. Add `history` to your INSTALLED_APPS setting.
2. Add `history.middleware.HistoryMiddleware` to the end of your `MIDDLEWARE_CLASSES`
   setting. (Or before, if another middleware needs the history table.)
3. Run `manage.py triggers` to create the history schema, history tables, and associated
   triggers.


Settings
========

* `HISTORY_SCHEMA` (default: `"history"`)
* `HISTORY_TABLE_PREFIX` (default: `""`)
* `HISTORY_TABLE_SUFFIX` (default: `""`)
* `HISTORY_RELATED_NAME` (default: `"history"`)
* `HISTORY_USER_VARIABLE` (default: `"history.user"`)
* `HISTORY_USER_FIELD` (default: `"user"`)
* `HISTORY_USER_MODEL` (default: `"django.contrib.auth.get_user_model"`)
* `HISTORY_MIDDLEWARE_IGNORE` (default: `[]`)
* `HISTORY_REQUEST_USER` (default: `"history.utils.get_request_user"`)
