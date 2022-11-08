from django.db.models import Model
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor
from zen_queries import QueriesDisabledError


class CachedObjectDoesNotExist(Exception):
    pass


class RelatedObjectsCache:
    def __enter__(self):
        self.cache = {}

        # store the original function so it can be restored on __exit__
        self.original_get_function = ForwardManyToOneDescriptor.__get__

        # replace the function with our custom one:
        ForwardManyToOneDescriptor.__get__ = getattr_or_get_object_from_cache(
            ForwardManyToOneDescriptor.__get__,
            self,
        )

        return self

    def __exit__(self, *exc):
        # reset to the original function to restore original behavior
        ForwardManyToOneDescriptor.__get__ = self.original_get_function

    def _cache_object(self, instance: Model):
        model_key = instance.__class__.__name__

        # get the model's cache by the instance's model name
        # if not already set, create an empty dict:
        model_cache: dict = self.cache.get(model_key, {})

        # if the entry already is cached, skip adding it again, to prevent infinite recursion:
        if instance.pk not in model_cache:

            # add an entry for the instance to the model cache:
            model_cache[instance.pk] = instance

            # update the cache's model entry:
            self.cache[model_key] = model_cache

            # then recursively cache each related object if it exists:
            for f in instance.__class__._meta.get_fields():
                if f.is_relation:
                    if f.many_to_one or f.one_to_one:
                        try:
                            related_instance = getattr(instance, f.name, None)
                            if related_instance:
                                self._cache_object(related_instance)

                        except QueriesDisabledError:
                            # look for it in the cache:
                            try:
                                related_model_cache = self.cache[
                                    f.related_model.__name__
                                ]
                                cached_related_instances = related_model_cache.values()
                                related_instance = next(
                                    filter(
                                        lambda x: getattr(x, f.field.attname)
                                        == instance.pk,
                                        cached_related_instances,
                                    ),
                                    None,
                                )

                                setattr(instance, f.related_name, related_instance)

                            except:
                                continue

                    elif f.one_to_many or f.many_to_many:
                        related_manager = getattr(instance, f.get_accessor_name())

                        try:
                            related_instances = list(related_manager.all())
                        except QueriesDisabledError:
                            # look for related instances in what has already been cached
                            related_instances = [
                                x
                                for x in self.cache.get(
                                    f.related_model.__name__, {}
                                ).values()
                                if getattr(x, f.field.attname, None) == instance.pk
                            ]

                            p = getattr(instance, "_prefetched_objects_cache", {})
                            p[f.get_accessor_name()] = related_instances
                            setattr(instance, "_prefetched_objects_cache", p)

                            continue

                        self._cache_objects(related_instances)

        else:
            # reassign the cached instance to the parent:
            pass

        return instance

    def _cache_objects(self, instances: list[Model]):
        for instance in instances:
            self._cache_object(instance)

        return instances

    def cache_results(self, *instances):
        for instance in instances:
            self._cache_object(instance)

    def get_object(self, model, pk):
        try:
            return self.cache[model][pk]
        except KeyError as e:
            return None


def getattr_or_get_object_from_cache(
    original_function,
    related_objects_cache: RelatedObjectsCache,
):
    def wrap(self, instance, cls=None):
        try:
            return original_function(self, instance, cls)

        except QueriesDisabledError as e:
            return related_objects_cache.get_object(
                model=self.field.related_model.__name__,
                pk=getattr(instance, self.field.attname),
            )

        except Exception as e:
            raise e

    return wrap
