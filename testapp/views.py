from django.http import JsonResponse

from history import session

from .models import Author, RandomData


def lifecycle(request):
    Author.objects.create(name="Dan Watson")
    return JsonResponse({})


@session(user=None)
def ignore(request):
    RandomData.objects.create()
    return JsonResponse({})
