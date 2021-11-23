from django.contrib.contenttypes.fields import GenericRelation
from django.db import models

from history.models import AbstractObjectHistory


class CustomHistory(AbstractObjectHistory):
    username = models.TextField()

    USER_FIELD = "username"

    class Meta(AbstractObjectHistory.Meta):
        db_table = "custom_history"


class Author(models.Model):
    name = models.CharField(max_length=100)

    history = GenericRelation(CustomHistory)


class Publisher(models.Model):
    name = models.CharField(max_length=100)


class Book(models.Model):
    title = models.CharField(max_length=100)
    authors = models.ManyToManyField(Author)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)
    year = models.IntegerField(null=True, blank=True)
