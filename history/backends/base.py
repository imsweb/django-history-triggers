import functools
import uuid

from django.apps import apps
from django.db import connections
from django.db.backends.utils import split_identifier, truncate_name
from django.utils import timezone
from django.utils.module_loading import import_string

from history import conf, get_history_model
from history.models import AbstractObjectHistory


class HistorySession:
    def __init__(self, backend, **fields):
        self.backend = backend
        self.parent = None
        self.fields = {}
        # Sanitize based on session fields in the object history model.
        for field in backend.session_fields():
            value = fields.get(field.name)
            if hasattr(value, "pk"):
                # This also covers AnonymousUser, which is not a Model instance.
                value = value.pk
            elif isinstance(value, uuid.UUID):
                value = value.hex
            if value is not None:
                self.fields[field.name] = value
        self.fields.setdefault("session_id", uuid.uuid4().hex)
        self.fields.setdefault("session_date", timezone.now().isoformat())

    @property
    def session_id(self):
        return uuid.UUID(self.fields["session_id"])

    @property
    def history(self):
        return get_history_model().objects.filter(session_id=self.session_id)

    def start_sql(self):
        raise NotImplementedError()

    def stop_sql(self):
        raise NotImplementedError()

    def start(self):
        self.backend.execute(*self.start_sql())

    def stop(self):
        self.backend.execute(*self.stop_sql())

    def __enter__(self):
        self.parent = self.backend.current_session
        self.backend.current_session = self
        self.start()
        return self

    def __exit__(self, *exc_details):
        self.stop()
        if self.parent:
            # Restart the parent session that we were nested within.
            self.parent.start()
        self.backend.current_session = self.parent

    def __call__(self, func):
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return wrapped


class HistoryBackend:
    session_class = HistorySession

    def __init__(self, alias):
        self.alias = alias
        self.current_session = None
        self.filter = (
            conf.FILTER if callable(conf.FILTER) else import_string(conf.FILTER)
        )

    @property
    def conn(self):
        c = connections[self.alias]
        c.ensure_connection()
        return c

    def install(self):
        pass

    def remove(self):
        pass

    def clear(self):
        get_history_model().objects.all().delete()

    def get_models(self):
        return [
            model
            for model in apps.get_models(include_auto_created=True)
            if not issubclass(model, AbstractObjectHistory)
            and model._meta.app_label not in conf.IGNORE_APPS
            and (model._meta.managed or conf.INCLUDE_UNMANAGED)
        ]

    def session_fields(self):
        HistoryModel = get_history_model()
        auto_populated = [
            "id",
            "change_type",
            "content_type",
            "object_id",
            "snapshot",
            "changes",
        ]
        for f in HistoryModel._meta.get_fields():
            if f.concrete and f.name not in auto_populated:
                yield f

    def model_fields(self, model, trigger_type):
        for f in model._meta.get_fields(include_parents=False):
            if f.many_to_many or not f.concrete:
                continue
            if self.filter(model, f, trigger_type):
                yield f

    def execute(self, sql, params=None):
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)

    def session(self, **fields):
        return self.session_class(self, **fields)

    def trigger_name(self, model, trigger_type, prefix="tr"):
        table_name = split_identifier(model._meta.db_table)[1]
        return truncate_name(
            "{}_{}_{}".format(prefix, table_name, trigger_type.name.lower())
        )

    def create_trigger(self, model, trigger_type):
        raise NotImplementedError()  # pragma: no cover

    def drop_trigger(self, model, trigger_type):
        raise NotImplementedError()  # pragma: no cover
