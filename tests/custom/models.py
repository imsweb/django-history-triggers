import uuid

from django.db import models
from django.utils import timezone

from history.models import AbstractObjectHistory, HistoryMixIn


class CustomHistory(AbstractObjectHistory):
    username = models.TextField()
    extra = models.TextField(null=True, blank=True)

    USER_FIELD = "username"

    class Meta(AbstractObjectHistory.Meta):
        db_table = "custom_history"


class Author(models.Model, HistoryMixIn):
    name = models.CharField(max_length=100)
    picture = models.BinaryField(null=True, blank=True)


class Book(models.Model, HistoryMixIn):
    title = models.CharField(max_length=100)
    authors = models.ManyToManyField(Author, related_name="books")
    year = models.IntegerField(null=True, blank=True)
    order = models.IntegerField(default=0)


class RandomData(models.Model, HistoryMixIn):
    ident = models.UUIDField(default=uuid.uuid4, unique=True)
    data = models.JSONField(default=dict)
    date = models.DateTimeField(default=timezone.now)


class UnmanagedHistory(AbstractObjectHistory):
    username = models.TextField()

    USER_FIELD = "username"

    class Meta(AbstractObjectHistory.Meta):
        db_table = "unmanaged_history"
        managed = False


class Untracked(models.Model):
    name = models.CharField(max_length=100)
