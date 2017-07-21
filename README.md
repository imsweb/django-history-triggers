Requirements
============

* Django 1.8+
* PostgreSQL database


Using Django History Triggers
=============================

1. Add "history" to your INSTALLED_APPS setting.
2. Add "history.middleware.HistoryMiddleware" to the end of your MIDDLEWARE_CLASSES setting.
   (Or before, if another middleware needs the history table)
3. Run "manage.py triggers" to create the history schema, history tables, and associated triggers.


Settings
========

* `HISTORY_SCHEMA` (default: "history")
* `HISTORY_USER_TEMP_TABLE` (default: "history_user")
* `HISTORY_USER_FIELD` (default: "user_id")
* `HISTORY_USER_TYPE` (default: "integer")
* `HISTORY_REQUEST_USER_FIELD` (default: "user")
* `HISTORY_REQUEST_USER_ATTRIBUTE` (default: "pk")
* `HISTORY_DB_ROLE` (default: settings.DATABASES['default']['USER'])
* `HISTORY_IGNORED_TABLES` (default: [])
* `HISTORY_IGNORED_PREFIXES` (default: ["django_", "auth_", "south_"])
* `HISTORY_IGNORED_TYPES` (default: ["bytea"])
* `HISTORY_IGNORED_COLUMNS` (default: [])
* `HISTORY_USE_TIMEZONES` (default: True)
* `HISTORY_DEFAULT_USER` (default: 0)
* `HISTORY_DEFAULT_USER_ERROR` (default: False)
* `HISTORY_MIDDLEWARE_IGNORE` (default: [settings.STATIC_URL, settings.MEDIA_URL])
* `HISTORY_JSON` (default: False)
