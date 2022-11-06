from django.db.models import Model
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor
from zen_queries import QueriesDisabledError


class CachedObjectDoesNotExist(Exception):
    pass


class RelatedObjectsCache:
    def __enter__(self):
        print("entering")

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

        print("exited")

    def cache_results(self, results: Model | list[Model]):
        try:
            return self.cache_objects(results)
        except TypeError:
            return self.cache_object(results)

    def cache_object(self, instance: Model):
        model_key = instance.__class__.__name__

        # get the model's cache by the instance's model name
        # if not already set, create an empty dict:
        model_cache: dict = self.cache.get(model_key, {})

        # if the entry does not already exist, exit the function:
        if instance.pk not in model_cache:

            # override the getattr method, so that subsequent attempts to access it will
            # check the cache if a query would be executed otherwise:
            # instance.related_objects_cache = self
            # instance.__getattribute__ = getattr_or_get_object_from_cache

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
                        except QueriesDisabledError:
                            continue

                        if related_instance:
                            self.cache_object(related_instance)

                    else:
                        related_manager = getattr(instance, f.name)

                        try:
                            related_instances = list(related_manager.all())
                        except QueriesDisabledError:
                            continue

                        self.cache_objects(related_instances)

        else:
            # reassign the cached instance to the parent:
            pass

        return instance

    def cache_objects(self, instances: list[Model]):
        for instance in instances:
            self.cache_object(instance)

        return instances

    def get_object(self, model, pk):
        try:
            return self.cache[model][pk]
        except KeyError as e:
            # raise CachedObjectDoesNotExist(
            #     f"Object not found in cache for {model} by pk {pk}"
            # )
            pass


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
