Requirements
============

* Django 3.0+
* PostgreSQL or SQLite database


Using Django History Triggers
=============================

1. Add `history` to your INSTALLED_APPS setting and migrate your database.
2. Add `history.middleware.HistoryMiddleware` to the end of your `MIDDLEWARE` setting.
3. Run `manage.py triggers` to install the trigger functions.


Settings
========

* `HISTORY_MODEL` (default: `"history.ObjectHistory"`)
* `HISTORY_MIDDLEWARE_IGNORE` (default: `[]`)
* `HISTORY_REQUEST_USER` (default: `"history.get_request_user"`)
* `HISTORY_ADMIN_ENABLED` (default: `True`)
