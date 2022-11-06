from django.http import HttpResponse
from .models import Alpha, Bravo, Charlie, Delta, Echo, Foxtrot
from zen_queries import (
    queries_disabled,
    queries_dangerously_enabled,
    QueriesDisabledError,
)
from django.shortcuts import render


def index(request):
    return render(request, "core/index.html", {"alphas": Alpha.objects.all()})


@queries_disabled()
def view_1(request, pk):
    from cache_related.cache_related import RelatedObjectsCache

    with RelatedObjectsCache() as related_objects_cache:
        related_objects_cache: RelatedObjectsCache

        with queries_dangerously_enabled():
            a = (
                Alpha.objects.select_related("bravo__charlie__delta__foxtrot")
                .prefetch_related("bravo__charlie__delta__echoes")
                .get(pk=pk)
            )

        related_objects_cache.cache_results(a)

        response = a.bravo.charlie.delta.alpha.bravo.value()

    return HttpResponse(response)
