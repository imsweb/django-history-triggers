from django.http import JsonResponse

from .models import Author


def lifecycle(request):
    Author.objects.create(name="Dan Watson")
    return JsonResponse({})
