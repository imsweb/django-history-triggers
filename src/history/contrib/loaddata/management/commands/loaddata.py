from django.core.management.commands import loaddata

from history import conf, get_backend


class Command(loaddata.Command):
    def handle(self, *args, **options):
        with get_backend().session(**conf.LOADDATA_CONTEXT):
            super().handle(*args, **options)
