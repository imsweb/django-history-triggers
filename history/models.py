from django.db import models


class HistoricalModel(models.Model):
    snapshot = models.JSONField(null=True, blank=True)
    changes = models.JSONField(null=True, blank=True)
    event_date = models.DateTimeField()
    event_type = models.CharField(max_length=1)

    class Meta:
        abstract = True

    def save(self, **kwargs):
        raise NotImplementedError()

    def delete(self, **kwargs):
        raise NotImplementedError()
