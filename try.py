from zen_queries import (
    queries_disabled,
    queries_dangerously_enabled,
)

from cache_related.cache_related import RelatedObjectsCache


@queries_disabled()
def main():
    from core.models import Alpha, Bravo, Charlie, Delta, Echo, Foxtrot

    with RelatedObjectsCache() as related_objects_cache:
        related_objects_cache: RelatedObjectsCache

        with queries_dangerously_enabled():
            a = (
                Alpha.objects.select_related("bravo__charlie__delta__foxtrot")
                .prefetch_related("bravo__charlie__delta__echoes")
                .get(pk=1)
            )

        related_objects_cache.cache_results(a)

        x = a.value()

    print(f"x: {x}")


if __name__ == "__main__":
    import os, django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    django.setup()

    main()
