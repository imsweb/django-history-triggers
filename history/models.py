import logging

from django.db import models
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from history import conf

logger = logging.getLogger(__name__)


class TriggerType(models.TextChoices):
    INSERT = "+", _("Insert")
    DELETE = "-", _("Delete")
    UPDATE = "~", _("Update")

    @property
    def snapshot(self):
        return "OLD" if self == TriggerType.DELETE else "NEW"

    @property
    def changes(self):
        return self == TriggerType.UPDATE


class HistoricalModel(models.Model):
    snapshot = models.JSONField(null=True, blank=True)
    changes = models.JSONField(null=True, blank=True)
    event_date = models.DateTimeField()
    event_type = models.CharField(max_length=1, choices=TriggerType.choices)

    class Meta:
        abstract = True

    def save(self, **kwargs):
        raise NotImplementedError()

    def delete(self, **kwargs):
        raise NotImplementedError()

    def get_user(self):
        try:
            user_id = getattr(self, conf.USER_FIELD, None)
            user_lookup = import_string(conf.USER_LOOKUP)
            return user_lookup(user_id)
        except Exception as ex:
            logger.warning(
                "Error in {}.get_user: {}".format(self.__class__.__name__, str(ex))
            )
            return None
