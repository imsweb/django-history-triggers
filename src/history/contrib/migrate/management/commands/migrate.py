from django.core.management.commands import migrate

from history import conf, get_backend


class Command(migrate.Command):
    def handle(self, *args, **options):
        with get_backend().session(**conf.MIGRATE_CONTEXT):
            super().handle(*args, **options)
