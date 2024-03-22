import re

from django.conf import settings

from .backends import get_backend, session  # noqa
from .utils import get_history_model  # noqa

__version__ = "3.4.6"
__version_info__ = tuple(
    int(num) if num.isdigit() else num
    for num in re.findall(r"([a-z\d]+)", __version__, re.I)
)


class _Configuration:
    def __init__(self, prefix=None, **defaults):
        self.prefix = prefix or self.__module__.split(".")[0]
        self.defaults = defaults

    def __getattr__(self, name):
        if name not in self.defaults:
            raise AttributeError(name)
        setting_name = "{}_{}".format(self.prefix, name).upper()
        return getattr(settings, setting_name, self.defaults[name])


conf = _Configuration(
    IGNORE_APPS=["admin", "contenttypes", "sessions"],
    MIDDLEWARE_IGNORE=[],
    FILTER="history.utils.default_filter",
    REQUEST_CONTEXT="history.utils.get_request_context",
    ADMIN_ENABLED=True,
    SNAPSHOTS=True,
    MIGRATE_CONTEXT={},
    LOADDATA_CONTEXT={},
    INCLUDE_UNMANAGED=True,
)
