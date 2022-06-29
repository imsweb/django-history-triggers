from django.urls import path

from . import views

urlpatterns = [
    path("lifecycle/", views.lifecycle),
]
