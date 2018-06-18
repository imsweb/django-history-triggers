from django.db import models


class Author (models.Model):
    name = models.CharField(max_length=100)


class Publisher (models.Model):
    name = models.CharField(max_length=100)


class Book (models.Model):
    title = models.CharField(max_length=100)
    authors = models.ManyToManyField(Author)
    publisher = models.ForeignKey(Publisher, on_delete=models.CASCADE)
    year = models.IntegerField(null=True, blank=True)
