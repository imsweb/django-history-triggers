from django.core.management.base import BaseCommand
from django.db import transaction

from history import backends
from history.models import TriggerType


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-q", "--quiet", action="store_true")
        subs = parser.add_subparsers(dest="action")
        subs.add_parser("create")
        subs.add_parser("drop")
        subs.add_parser("clear")

    def handle_create(self, backend, **options):
        backend.create_schema()
        for model in backend.get_models():
            if backend.create_history_table(model):
                if not options["quiet"]:
                    print("Created history table for {}".format(model._meta.label))
            if not options["quiet"]:
                print("Creating triggers for {}".format(model._meta.label))
            for trigger_type in TriggerType:
                name = backend.create_trigger(model, trigger_type)
                if options["verbosity"] > 1 and not options["quiet"]:
                    print("  + {}".format(name))

    def handle_drop(self, backend, **options):
        for model in backend.get_models():
            if not options["quiet"]:
                print("Dropping triggers for {}".format(model._meta.label))
            for trigger_type in TriggerType:
                backend.drop_trigger(model, trigger_type)

    def handle_clear(self, backend, **options):
        backend.drop_schema()

    @transaction.atomic
    def handle(self, **options):
        backend = backends.get_backend()
        action = options.get("action") or "create"
        getattr(self, "handle_{}".format(action))(backend, **options)
