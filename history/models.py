from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from .utils import get_history_model


class TriggerType(models.TextChoices):
    INSERT = "I", _("Insert")
    DELETE = "D", _("Delete")
    UPDATE = "U", _("Update")

    @property
    def snapshot(self):
        return "OLD" if self == TriggerType.DELETE else "NEW"

    @property
    def changes(self):
        return self == TriggerType.UPDATE


class AbstractObjectHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    session_id = models.UUIDField(editable=False)
    session_date = models.DateTimeField(editable=False)
    change_type = models.CharField(
        max_length=1, choices=TriggerType.choices, editable=False
    )
    content_type = models.ForeignKey(
        ContentType,
        related_name="+",
        on_delete=models.CASCADE,
        editable=False,
    )
    object_id = models.BigIntegerField(editable=False)
    snapshot = models.JSONField(null=True, blank=True, editable=False)
    changes = models.JSONField(null=True, blank=True, editable=False)

    source = GenericForeignKey("content_type", "object_id")

    USER_FIELD = None

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]

    def get_user(self):
        return getattr(self, self.USER_FIELD) if self.USER_FIELD else None

    def __str__(self):
        # Use the ContentType cache instead of FK lookups every time.
        ct = ContentType.objects.get_for_id(self.content_type_id)
        return "{} {}({})".format(
            self.get_change_type_display(),
            ct.model_class()._meta.label,
            self.object_id,
        )


class ObjectHistory(AbstractObjectHistory):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        db_constraint=False,
        related_name="object_history",
        on_delete=models.DO_NOTHING,
        editable=False,
    )

    USER_FIELD = "user"

    class Meta(AbstractObjectHistory.Meta):
        db_table = "object_history"
        swappable = "HISTORY_MODEL"
        verbose_name_plural = _("object history")


class HistoryDescriptor:
    def __get__(self, instance, owner=None):
        ct = ContentType.objects.get_for_model(instance or owner)
        qs = get_history_model().objects.filter(content_type=ct)
        if instance:
            qs = qs.filter(object_id=instance.pk)
        return qs


class HistoryMixIn:
    history = HistoryDescriptor()
