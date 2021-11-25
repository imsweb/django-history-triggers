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
3. Run `manage.py triggers` to install the trigger functions.


## Settings

* `HISTORY_MODEL` (default: `"history.ObjectHistory"`)
* `HISTORY_IGNORE_APPS` (default: `["admin", "contenttypes", "sessions"]`)
* `HISTORY_MIDDLEWARE_IGNORE` (default: `[]`)
* `HISTORY_REQUEST_CONTEXT` (default: `"history.get_request_context"`)
* `HISTORY_ADMIN_ENABLED` (default: `True`)
