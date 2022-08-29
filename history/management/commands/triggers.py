from django.core.management.base import BaseCommand
from django.db import DEFAULT_DB_ALIAS

from history import backends
from history.models import TriggerType


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-q",
            "--quiet",
            action="store_true",
            help="Suppresses all output.",
        )
        parser.add_argument(
            "-d",
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Which database to operate on. Defaults to `default`.",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clears all object history.",
        )
        subs = parser.add_subparsers(dest="action")
        subs.add_parser("enable")
        subs.add_parser("disable")
        subs.add_parser("session")

    def handle_enable(self, backend, **options):
        if options["clear"]:
            backend.clear()
        backend.install()
        for model in backend.get_models():
            if not options["quiet"]:
                print("Creating triggers for {}".format(model._meta.label))
            for trigger_type in TriggerType:
                name, fields = backend.create_trigger(model, trigger_type)
                if options["verbosity"] > 1 and not options["quiet"]:
                    print("  + {}{}".format(name, "" if fields else " (SKIPPED)"))
                    if options["verbosity"] > 2 and not options["quiet"]:
                        print("    - {}".format(", ".join(fields)))

    def handle_disable(self, backend, **options):
        for model in backend.get_models():
            if not options["quiet"]:
                print("Dropping triggers for {}".format(model._meta.label))
            for trigger_type in TriggerType:
                backend.drop_trigger(model, trigger_type)
        backend.remove()
        if options["clear"]:
            backend.clear()

    def handle_session(self, backend, **options):
        conn = backend.conn
        fields = {}
        for f in backend.session_fields():
            if f.name in ("session_id", "session_date"):
                continue
            value = input("{} [{}]: ".format(f.name, f.db_type(conn)))
            fields[f.name] = value
        s = backend.session(**fields)
        sql, params = s.start_sql()
        print(sql % tuple("'{}'".format(p) for p in params))

    def handle(self, **options):
        backend = backends.get_backend(options["database"], cache=False)
        action = options.get("action") or "enable"
        getattr(self, "handle_{}".format(action))(backend, **options)
