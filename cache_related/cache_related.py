from django.db.models import Model
from django.db.models.fields.related_descriptors import ForwardManyToOneDescriptor
from zen_queries import QueriesDisabledError


class CachedObjectDoesNotExist(Exception):
    pass


class ObjectAlreadyCached(Exception):
    pass


class RelatedObjectsCache:
    def __enter__(self):
        self.relationships = {}
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

                    # register the relationship in self.relationships:
                    if f.many_to_one or f.one_to_one:
                        try:
                            ff = f
                            self.relationships[
                                (
                                    f"{ff.remote_field.model.__name__}.{ff.remote_field.get_accessor_name()}",
                                    f"{ff.model.__name__}.{ff.attname}",
                                )
                            ] = f

                        except AttributeError as e:
                            ff = f.remote_field
                            self.relationships[
                                (
                                    f"{ff.remote_field.model.__name__}.{ff.remote_field.get_accessor_name()}",
                                    f"{ff.model.__name__}.{ff.attname}",
                                )
                            ] = f

                    elif f.one_to_many or f.many_to_many:
                        self.relationships[
                            (
                                f"{f.model.__name__}.{f.get_accessor_name()}",
                                f"{f.remote_field.model.__name__}.{f.remote_field.attname}",
                            )
                        ] = f

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
                            continue

                        self._cache_objects(related_instances)

        else:
            raise ObjectAlreadyCached(
                f"'{model_key}' object with id '{instance.pk}' already cached"
            )

        return instance

    def _cache_objects(self, instances: list[Model]):
        for instance in instances:
            self._cache_object(instance)

        return instances

    def cache_results(self, *instances):

        # first, add all the new instances to the cache
        for instance in instances:
            self._cache_object(instance)

        # then, add all related objects to their parents' _prefetched_objects_cache
        for key, field in self.relationships.items():
            m = field.model
            m_field = field.field_name
            m_instances = self.cache[m.__name__].values()

            rm = field.related_model
            rm_field = field.remote_field.attname
            rm_instances = self.cache[rm.__name__].values()

            for x in m_instances:
                matching = [
                    y
                    for y in rm_instances
                    if getattr(y, rm_field, None) == getattr(x, m_field, None)
                ]

                if field.one_to_one or field.many_to_one:
                    matching = next(iter(matching), None)

                    setattr(
                        x,
                        field.name,
                        matching,
                    )

                elif field.one_to_many or field.many_to_many:

                    p = getattr(x, "_prefetched_objects_cache", {})
                    p[field.get_accessor_name()] = matching
                    setattr(x, "_prefetched_objects_cache", p)

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
