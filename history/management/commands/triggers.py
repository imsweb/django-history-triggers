from django.core.management.base import BaseCommand
from django.db import transaction

from history import TriggerType, backends


class Command(BaseCommand):
    def add_arguments(self, parser):
        subs = parser.add_subparsers(dest="action")
        subs.add_parser("create")
        subs.add_parser("drop")
        subs.add_parser("clear")

    def handle_create(self, backend, **options):
        backend.create_schema()
        for model in backend.get_models():
            if backend.create_history_table(model):
                print("Created history table for {}".format(model))
            print("Creating triggers for {}".format(model))
            for trigger_type in TriggerType:
                backend.create_trigger(model, trigger_type)

    def handle_drop(self, backend, **options):
        for model in backend.get_models():
            print("Dropping triggers for {}".format(model))
            for trigger_type in TriggerType:
                backend.drop_trigger(model, trigger_type)

    def handle_clear(self, backend, **options):
        backend.drop_schema()

    @transaction.atomic
    def handle(self, **options):
        backend = backends.get_backend()
        action = options.get("action") or "create"
        getattr(self, "handle_{}".format(action))(backend, **options)
