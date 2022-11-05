from django.db.models import Model
from zen_queries import QueriesDisabledError


class CachedObjectDoesNotExist(Exception):
    pass


class RelatedObjectsCache2:
    def __init__(self):
        self.cache = {}

    def cache_object(self, instance: Model):
        model_key = instance.__class__.__name__

        # get the model's cache by the instance's model name
        # if not already set, create an empty dict:
        model_cache: dict = self.cache.get(model_key, {})

        # add an entry for the instance to the model cache:
        model_cache[instance.pk] = instance

        # update the cache's model entry:
        self.cache[model_key] = model_cache

    def cache_objects(self, instances: list[Model]):
        for instance in instances:
            self.cache_object(instance)

    def get_object(self, model, pk):
        try:
            return self.cache[model][pk]
        except KeyError as e:
            raise CachedObjectDoesNotExist(
                f"Object not found in cache for {model} by pk {pk}"
            )


class RelatedObjectsCache3:
    def __init__(self):
        self.cache = {}

    def cache_object(self, instance: Model):
        model_key = instance.__class__.__name__

        # get the model's cache by the instance's model name
        # if not already set, create an empty dict:
        model_cache: dict = self.cache.get(model_key, {})

        # if the entry already exists, exit the function:
        if instance.pk in model_cache:
            return

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

    def cache_objects(self, instances: list[Model]):
        for instance in instances:
            self.cache_object(instance)

    def get_object(self, model, pk):
        try:
            return self.cache[model][pk]
        except KeyError as e:
            raise CachedObjectDoesNotExist(
                f"Object not found in cache for {model} by pk {pk}"
            )
