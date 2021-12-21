from django.db import models

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
