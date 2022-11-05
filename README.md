# django-cache-related

## The Problem

Complex model structures with multiple relationships among models are difficult to properly select/prefetch_related. Or, even when properly selected/prefetched, it can be challenging to access the a deeply-nested, prefetched object from the right attribute so as to avoid an additional query.

For example, if we select an `Alpha` object, and its related `Bravo`, `Charlie`, and `Delta` objects...

``` py
alpha = Alpha.objects.select_related('bravo__charlie__delta').get(pk=1)
```

...we can do this without generating any more queries:
``` py
alpha.bravo.charlie.delta
```

But this will, because it was not select_related:
``` py
alpha.delta
```

We can fix it like this...
``` py
alpha = Alpha.objects.select_related(
    'bravo__charlie__delta',
    'delta',
).get(pk=1)
```

But if `Delta` has any more relationships, we need twice as many selects/prefetches:
``` py
alpha = Alpha.objects.select_related(
    'bravo__charlie__delta__foxtrot',
    'delta__foxtrot',
).prefetch_related(
    'bravo__charlie__delta__echoes',
    'delta__echoes',
).get(pk=1)
```

And, if we need to access `echo.delta.alpha`, we start going in circles, like in this case where we have to select the related `Alpha` object, which was the one we started with in the first place:
``` py
alpha = Alpha.objects\
    .select_related('bravo__charlie__delta')\
    .prefetch_related(
        Prefetch(
            lookup='bravo__charlie__delta__echoes',
            queryset=Echo.objects.select_related('delta__alpha'),
        )
    )\
    .get(pk=1)
```

While it's theoretically possible to optimize queries so everything is fetched up front, there are cases I've found where this is not practical.

## The Solution

Create some sort of caching strategy or context manager that makes it possible to fetch simpler queries up front, then look up a related object by primary key if attempting to get it by attribute would generate a new query to the database.

``` py
alpha = Alpha.objects.select_related('bravo__charlie__delta').get(pk=1)

# we can access `delta` through `bravo` and `charlie`:
delta = alpha.bravo.charlie.delta

# but not from `alpha` directly:
alpha.delta

# nor can we access `alpha` from `delta` in reverse:
delta.alpha

# however, we'd intercept the attempt, and look it up in our cached data instead,
# and if it doesn't exist there, then raise an exception or allow the original query to be executed:
try:
    cached_related_objects['Alpha'][delta.alpha_id]
except KeyError as e:
    raise CachedRelatedObjectNotFound(f'Could not find an object of type Alpha with id {delta.alpha_id}')
```

