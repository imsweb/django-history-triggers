## 3.6.0

* Switched to [uv](https://docs.astral.sh/uv/) for development
* Ensure backend cache is thread-safe (#11)


## 3.5.0

* Removed `TriggerType.snapshot` so that delete triggers will now record snapshots.
* Added `TriggerType.snapshot_of` to determine whether snapshots are of `OLD` or `NEW`.


## 3.4.7

* Added a `HISTORY_IGNORE_MODELS` setting to ignore individual models. This should be a
  list of lowercase `app_label.model_name` models to exclude.


## 3.4.6

* Properly specify database alias for ContentType queries


## 3.4.5

* Properly specify database alias for Django queries in the history backends


## 3.4.4

* `CASCADE` when dropping the `history_record` function.


## 3.4.3

* Added a `paused` context manager to `HistorySession`, to allow for temporarily
  suspending history recording during a session.


## 3.4.2

*Yanked to correct a bad API decision*


## 3.4.1

* Added a `HISTORY_INCLUDE_UNMANAGED` setting to determine if history should be created
  for unmanaged (`managed = False`) models. Defaults to `True`.


## 3.4.0

* Allow `HistorySession` instances to be used as decorators, expose `history.session`
  as a convenience method that automatically calls `get_backend`
* Unit tests for `HISTORY_MIDDLEWARE_IGNORE`


## 3.3.0

* [sqlite] Better handling of nested JSON within update trigger `changes`
* Added a `session` CLI subcommand (`manage.py triggers session`) to output the SQL for
  starting a history session (does not work for sqlite, which uses user-defined
  functions for history sessions).


## 3.2.0

* Added `history.contrib.migrate` and `history.contrib.loaddata` apps that provide
  wrappers of Django management commands that run within history sessions


## 3.1.1

* Included missing `admin_history.html` template in distribution


## 3.1.0

* Added a `HISTORY_FILTER` setting for excluding models/fields from history, and exclude
  `BinaryField`s from history by default
* Added a `HISTORY_SNAPSHOTS` setting to allow disabling full object snapshots
* Store JSONField values in `snapshot` and `changes` as actual JSON on SQLite


## 3.0.1

* Fixed support for older versions of Postgres without `CREATE OR REPLACE TRIGGER`
* Included README in PyPI


## 3.0.0

* Store all history in a single table, using `ContentType`s
* Record a JSON snapshot and changes (when appropriate) for each historical entry
* Introduce a session-based API for better grouping of historical changes
* Allow customization of object history using a swappable model
* Added SQLite support
