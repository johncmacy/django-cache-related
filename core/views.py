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
    """demonstrate the problem"""

    with queries_dangerously_enabled():
        a = (
            Alpha.objects.select_related("bravo__charlie__delta__foxtrot")
            .prefetch_related("bravo__charlie__delta__echoes")
            .get(pk=pk)
        )

    # these will pass:
    a.bravo.charlie.delta.foxtrot
    a.bravo.charlie.delta.echoes.all()

    # this will fail:
    a.bravo.charlie.delta.alpha

    return HttpResponse(a.value())


@queries_disabled()
def view_2(request, pk):
    """manual proof-of-concept"""

    from cache_related.cache_related import RelatedObjectsCache2 as RelatedObjectsCache

    cached_objects = RelatedObjectsCache()

    with queries_dangerously_enabled():
        a = (
            Alpha.objects.select_related("bravo__charlie__delta__foxtrot")
            .prefetch_related("bravo__charlie__delta__echoes")
            .get(pk=pk)
        )

    # manually add objects to the cache:
    cached_objects.cache_object(a)
    cached_objects.cache_object(a.bravo)
    cached_objects.cache_object(a.bravo.charlie)
    cached_objects.cache_object(a.bravo.charlie.delta)
    cached_objects.cache_objects(a.bravo.charlie.delta.echoes.all())
    cached_objects.cache_object(a.bravo.charlie.delta.foxtrot)

    # these will pass:
    a.bravo.charlie.delta.foxtrot
    a.bravo.charlie.delta.echoes.all()

    # this will raise a QueriesDisabledError:
    try:
        a2 = a.bravo.charlie.delta.alpha

    except QueriesDisabledError:
        # but we can catch the exception, and look it up in the cache instead:

        a2 = cached_objects.get_object(
            Alpha.__name__,
            a.bravo.charlie.delta.alpha_id,
        )

    return HttpResponse(a2.value())


@queries_disabled()
def view_3(request, pk):
    """so how do we automate it?"""

    from cache_related.cache_related import RelatedObjectsCache3 as RelatedObjectsCache

    # we still need control over when it gets used, so i think
    # manually creating it in the view is still ok
    cached_objects = RelatedObjectsCache()

    # we then fetch the data like normal
    with queries_dangerously_enabled():
        a = (
            Alpha.objects.select_related("bravo__charlie__delta__foxtrot")
            .prefetch_related("bravo__charlie__delta__echoes")
            .get(pk=pk)
        )

    # and then add it to the cache:
    cached_objects.cache_object(a)

    # and then it would be convenient if it recursively navigates
    # the tree of selected/prefetched related objects, and caches each
    # this is working, see RelatedObjectsCache3.cache_object()

    # now, it would be convenient if this happened automatically,
    # without having to wrap every attempt to access an attribute
    # in a try/except statement:
    a2 = a.bravo.charlie.delta.alpha

    return HttpResponse(a2.value())
