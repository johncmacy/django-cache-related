from django.db.models import Model, Field
from django.db.models.fields.related import (
    ForeignKey,
    ManyToManyField,
    ManyToManyRel,
    ManyToOneRel,
    OneToOneField,
    OneToOneRel,
)
from zen_queries import QueriesDisabledError
from typing import Any, Union
from uuid import UUID
from source_documents_app.export_to_excel.excel_table import set_attribute_by_accessor


class CachedObjectDoesNotExist(Exception):
    pass


class ObjectAlreadyCached(Exception):
    pass


class RelationshipTracker:
    def __init__(self, field: Field):
        self.field = field

    @property
    def model(self) -> Model:
        return self.field.model

    @property
    def field_to_cache_on(self) -> str:

        if self.field.__class__ == ForeignKey:
            return f'.{self.field.name}'

        elif self.field.__class__ == ManyToOneRel:
            return f'._prefetched_objects_cache[{self.field.get_accessor_name()}]'

        elif self.field.__class__ == OneToOneField:
            return f'.{self.field.name}'

        elif self.field.__class__ == OneToOneRel:
            return f'.{self.field.name}'

        elif self.field.__class__ == ManyToManyField:
            return f'.{self.field.name}'

        elif self.field.__class__ == ManyToManyRel:
            return f'.{self.field.name}'

    @property
    def field_to_match(self) -> str:

        if self.field.__class__ == ForeignKey:
            return self.field.attname

        elif self.field.__class__ == ManyToOneRel:
            # doesn't work:
            # return self.field.field_name

            # works for:
            # Proposal.phases,
            # .proposal_users,
            # .events,
            # .phases,
            # .solutions,
            # .revisions,
            # .option_groups,
            # .clins,
            # User.proposaluser_set,
            # .proposalrevision_set,
            # .source_documents,
            # OptionGroup.options,
            # Phase.acquisition_groups,
            # ProposalType.proposal_set,
            # MissionClass.proposal_set,
            # SourceDocument.clins,

            # but not for:
            # BusinessUnit.attritionratesprocedure_set,
            # return self.field.target_field.attname

            # works:
            return self.field.field.remote_field.field_name

        elif self.field.__class__ == OneToOneField:
            return self.field.attname

        elif self.field.__class__ == OneToOneRel:
            return self.field.field_name

        elif self.field.__class__ == ManyToManyField:
            # since 'id' is the name of the PK in both cases,
            # I can't deduce whether it's referring to model.id or related_model.id
            # need to set up a scenario where the PK fields have different names in
            # order to be certain
            return self.field.target_field.attname

        elif self.field.__class__ == ManyToManyRel:
            return self.field.target_field.attname

    @property
    def related_model(self) -> Model:
        return self.field.related_model

    @property
    def remote_field_to_match(self) -> str:

        if self.field.__class__ == ForeignKey:
            # not right:
            # Proposal.escalation_rates_procedure_id == EscalationRatesProcedure.escalation_rates_procedure_id
            # return self.field.attname

            # should be:
            # Proposal.escalation_rates_procedure_id == EscalationRatesProcedure.sourcedocument_ptr
            return self.field.target_field.attname

        elif self.field.__class__ == ManyToOneRel:
            # doesn't work:
            # return self.field.field_name

            # works for:
            # Proposal.revisions,
            # .proposal_users,
            # .events,
            # .phases,
            # .revisions,
            # .option_groups,
            # .clins,
            # User.proposaluser_set,
            # .proposalrevision_set,
            # .source_documents,
            # Phase.acquisition_groups,
            # ProposalType.proposal_set,
            # MissionClass.proposal_set,
            return self.field.remote_field.attname

        elif self.field.__class__ == OneToOneField:
            return self.field.remote_field.field_name
            # return self.field.attname

        elif self.field.__class__ == OneToOneRel:
            return self.field.field_name

        elif self.field.__class__ == ManyToManyField:
            # since 'id' is the name of the PK in both cases,
            # I can't deduce whether it's referring to model.id or related_model.id
            # need to set up a scenario where the PK fields have different names in
            # order to be certain
            return self.field.target_field.attname

        elif self.field.__class__ == ManyToManyRel:
            return self.field.target_field.attname

    def cache_related_data(self, instance: Model, cache: dict[str, dict[Any, Model]]):
        '''
        Given an instance of type `self.model`,
        find related data in the cache
        where `self.field` matches `self.remote_field_to_match`
        '''

        related_model_instances = cache\
            .get(self.related_model.__name__, {})\
            .values()

        value = filter(
            lambda o: (
                getattr(instance, self.field_to_match)
                == getattr(o, self.remote_field_to_match)
            ),
            related_model_instances,
        )

        if self.field.many_to_many:
            value = list(value)

        elif self.field.one_to_many:
            value = list(value)

        elif self.field.one_to_one:
            value = next(value, None)

        elif self.field.many_to_one:
            value = next(value, None)

        if value:
            set_attribute_by_accessor(
                instance,
                self.field_to_cache_on,
                value,
            )

    def __hash__(self):
        return hash(
            (
                self.model,
                self.field_to_cache_on,
                self.field_to_match,
                self.related_model,
                self.remote_field_to_match,
            )
        )

    def __eq__(self, __o):
        return hash(self) == hash(__o)

    def __repr__(self) -> str:
        return f'{self.model.__name__}{self.field_to_cache_on} = {self.related_model.__name__} WHERE ({self.model.__name__}.{self.field_to_match} == {self.related_model.__name__}.{self.remote_field_to_match})'


class RelatedObjectsCache:
    relationships: dict[str, set[RelationshipTracker]] = {}
    cache: dict[Union[str, int, UUID], dict] = {}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def _add_object_to_cache(self, instance: Model):

        model_key = instance.__class__.__name__

        # get the model's cache by the instance's model name
        # if not already set, create an empty dict:
        self.cache.setdefault(model_key, {})
        model_cache: dict = self.cache[model_key]

        # if this exact instance has already been cached, skip adding
        # it again to prevent infinite recursion
        # note the use of `is not` vs `!=` to check if it is the same
        # object stored in memory - if multiple objects exist for the
        # same model/pk, we want to scan all in case they have
        # different selected/prefetched related objects
        if model_cache.get(instance.pk) is not instance:

            # assign it to the cache:
            model_cache[instance.pk] = instance

            # then recursively cache each related object if it exists:
            model_fields = instance.__class__._meta.get_fields()
            relationship_fields = [f for f in model_fields if f.is_relation]
            for f in relationship_fields:
                relationship_tracker = RelationshipTracker(field=f)

                self.relationships[model_key] = {
                    *self.relationships.get(model_key, []),
                    relationship_tracker,
                }

                if f.many_to_one or f.one_to_one:
                    try:
                        related_instance = getattr(instance, f.name, None)
                        if related_instance:
                            self._add_object_to_cache(related_instance)

                    except QueriesDisabledError:

                        # skip for now, it will be cached later after the
                        # initial objects have been cached
                        continue

                else:

                    if f.__class__ == ManyToOneRel:
                        related_manager = getattr(
                            instance,
                            f.get_accessor_name()
                        )

                    elif f.__class__ == ManyToManyField:
                        related_manager = getattr(
                            instance,
                            f.attname
                        )

                    elif f.__class__ == ManyToManyRel:
                        related_manager = getattr(
                            instance,
                            f.get_accessor_name()
                        )

                    try:
                        related_instances = list(related_manager.all())
                    except QueriesDisabledError:
                        continue
                    except:
                        continue

                    for related_instance in related_instances:
                        self._add_object_to_cache(related_instance)

        return instance

    def cache_results(self, *instances):

        # first, add all the new instances to the cache:
        for instance in instances:
            self._add_object_to_cache(instance)

        # then, add all related objects to each other:

        relationships_with_cached_data = sorted(
            [
                r
                for relationships in self.relationships.values()
                for r in relationships
                if r.model.__name__ in self.cache
                and r.related_model.__name__ in self.cache
            ],
            key=lambda x: (x.model.__name__, x.related_model.__name__)
        )

        for r in relationships_with_cached_data:
            # get all model instances first:
            model_instances = self.cache[r.model.__name__].values()

            for model_instance in model_instances:
                r.cache_related_data(model_instance, self.cache)
