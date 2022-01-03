from .backends import get_backend  # noqa
from .utils import get_history_model, get_request_context  # noqa

__version__ = "3.0.1"
__version_info__ = tuple(int(num) for num in __version__.split(".") if num.isdigit())
