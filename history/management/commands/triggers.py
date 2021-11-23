from django.core.management.base import BaseCommand

from history import backends
from history.models import TriggerType


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("-q", "--quiet", action="store_true")
        subs = parser.add_subparsers(dest="action")
        subs.add_parser("enable")
        subs.add_parser("disable")

    def handle_enable(self, backend, **options):
        backend.install()
        for model in backend.get_models():
            if not options["quiet"]:
                print("Creating triggers for {}".format(model._meta.label))
            for trigger_type in TriggerType:
                name = backend.create_trigger(model, trigger_type)
                if options["verbosity"] > 1 and not options["quiet"]:
                    print("  + {}".format(name))

    def handle_disable(self, backend, **options):
        for model in backend.get_models():
            if not options["quiet"]:
                print("Dropping triggers for {}".format(model._meta.label))
            for trigger_type in TriggerType:
                backend.drop_trigger(model, trigger_type)
        backend.remove()

    def handle(self, **options):
        backend = backends.get_backend()
        action = options.get("action") or "enable"
        getattr(self, "handle_{}".format(action))(backend, **options)
