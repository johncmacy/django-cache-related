from django.http import HttpResponse
from .models import Alpha, Bravo, Charlie, Delta, Echo, Foxtrot
from zen_queries import queries_disabled, queries_dangerously_enabled
from django.shortcuts import render


def index(request):
    return render(request, "core/index.html", {"alphas": Alpha.objects.all()})


@queries_disabled()
def alpha(request, pk):

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
