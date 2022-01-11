from django.conf import settings

from .backends import get_backend  # noqa
from .utils import get_history_model  # noqa

__version__ = "3.1.0"
__version_info__ = tuple(int(num) for num in __version__.split(".") if num.isdigit())


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
)
