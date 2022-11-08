from zen_queries import (
    queries_disabled,
    queries_dangerously_enabled,
)

from cache_related.cache_related import RelatedObjectsCache


@queries_disabled()
def main():
    from django.db.models import Prefetch
    from core.models import Alpha, Bravo, Charlie, Delta, Echo, Foxtrot

    with RelatedObjectsCache() as related_objects_cache:
        related_objects_cache: RelatedObjectsCache

        with queries_dangerously_enabled():
            a = list(Alpha.objects.all())
            b = list(Bravo.objects.all())
            c = list(Charlie.objects.all())
            d = list(Delta.objects.all())
            e = list(Echo.objects.all())
            f = list(Foxtrot.objects.all())

        related_objects_cache.cache_results(
            *f,
            *e,
            *d,
            *c,
            *b,
            *a,
        )

        y = [x.value() for x in a]

    print(f"x: {y}")


if __name__ == "__main__":
    import os, django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    django.setup()

    main()
