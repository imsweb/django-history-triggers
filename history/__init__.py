import enum

__version_info__ = (3, 0, 0)
__version__ = ".".join(str(i) for i in __version_info__)

default_app_config = "history.apps.HistoryConfig"


class TriggerType(enum.Enum):
    INSERT = "+"
    DELETE = "-"
    UPDATE = "~"

    @property
    def snapshot(self):
        return "OLD" if self == TriggerType.DELETE else "NEW"

    @property
    def changes(self):
        return self == TriggerType.UPDATE
