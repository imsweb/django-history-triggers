import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from . import conf

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
    id = models.BigAutoField(primary_key=True)
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
        return getattr(self, conf.USER_FIELD)
