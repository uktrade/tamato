from __future__ import annotations

import re
from datetime import datetime
from typing import List
from typing import Tuple
from typing import Type

from django.contrib.postgres.fields import DateTimeRangeField
from django.db import models
from django.db.models import Field
from django.db.models import Func
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import QuerySet
from django.db.models import Subquery
from django.template import loader
from django.utils import timezone
from polymorphic.managers import PolymorphicManager
from polymorphic.models import PolymorphicModel
from polymorphic.query import PolymorphicQuerySet
from treebeard.mp_tree import MP_NodeQuerySet

from common import exceptions
from common import validators
from workbaskets.validators import WorkflowStatus


class InvalidQueryError(Exception):
    pass


class RowToJsonSubquery(Subquery):
    def as_sql(self, compiler, connection, template=None, **extra_context):
        """
        Django Subquery Expressions can't be compiled down the chain as they are
        unaware of their parents. This presents a problem when a child expression
        needs information from its parent.

        In this case the row_to_json postgres function needs to know the table
        alias (or table name) being used. Django always uses aliases in subqueries.

        To remedy this the subquery itself resolves the initial row_to_json
        expression without the table name. Then, with some regex, it finds the
        table name and retroactively fills it in as an argument for the row_to_json
        function.

        The majority of this function is a direct copy from django at version 3.1.
        """
        connection.ops.check_expression_support(self)
        template_params = {**self.extra, **extra_context}
        subquery_sql, sql_params = self.query.as_sql(compiler, connection)
        subquery = subquery_sql[1:-1]
        template = template or template_params.get("template", self.template)

        match = re.search(r".*FROM\s\".*\"\s(\w*\d*)\s((WHERE)|(INNER)).*", subquery)
        if not match:
            raise InvalidQueryError("This subquery doesn't have any table aliases")
        template_params["subquery"] = subquery.replace(
            "row_to_json()", f"row_to_json({match.group(1)})"
        )

        sql = template % template_params
        return sql, sql_params


class RowToJson(Func):
    """
    Uses the `row_to_json` postgres function in a query.

    Must be used in conjunction with `RowToJsonSubquery` so as to add
    the proper arguments to the function.

    The `row_to_json` function requires the table alias as an argument.
    This is currently inacessible from django's `Func` implementation.
    """

    function = "row_to_json"
    output_field = models.CharField()


class TrackedModelQuerySet(PolymorphicQuerySet):
    def current(self) -> TrackedModelQuerySet:
        """
        Get all the current versions of the model being queried.

        Current is defined as the last row relating to the history of an object.
        this may include current operationally live rows, it will often also mean
        rows that are not operationally live yet but may be soon. It could also include
        rows which were operationally live, are no longer operationally live, but have
        no new row to supercede them.

        If done from the TrackedModel this will return the current objects for all tracked
        models.
        """
        return self.filter(successor__isnull=True)

    def since_transaction(self, transaction_id: int) -> QuerySet:
        """
        Get all instances of an object since a certain transaction (i.e. since a particular
        workbasket was accepted).

        This will not include objects without a transaction ID - thus excluding rows which
        have not been accepted yet.

        If done from the TrackedModel this will return all objects from all transactions since
        the given transaction.
        """
        return self.filter(workbasket__transaction__id__gt=transaction_id)

    def as_at(self, date: datetime) -> TrackedModelQuerySet:
        """
        Return the instances of the model that were represented at a particular date.

        If done from the TrackedModel this will return all instances of all tracked models
        as represented at a particular date.
        """
        return self.filter(valid_between__contains=date)

    def active(self) -> TrackedModelQuerySet:
        """
        Return the instances of the model that are represented at the current date.

        If done from the TrackedModel this will return all instances of all tracked models
        as represented at the current date.
        """
        return self.as_at(timezone.now())

    def get_version(self, **kwargs) -> TrackedModel:
        for field in self.model.identifying_fields:
            if field not in kwargs:
                raise exceptions.NoIdentifyingValuesGivenError(
                    f"Field {field} expected but not found."
                )
        return self.get(**kwargs)

    def get_latest_version(self, **kwargs) -> TrackedModel:
        """
        Gets the latest version of a specific object.
        """
        return self.get_version(successor__isnull=True, **kwargs)

    def get_current_version(self, **kwargs) -> TrackedModel:
        """
        Gets the current version of a specific object.
        """
        return self.active().get_version(**kwargs)

    def get_first_version(self, **kwargs) -> TrackedModel:
        """
        Get the original version of a specific object.
        """
        return self.get_version(predecessor__isnull=True, **kwargs)

    def with_workbasket(self, workbasket) -> TrackedModelQuerySet:
        """
        Add the latest versions of objects from the specified workbasket.
        """

        if workbasket is None:
            return self

        query = Q()

        # get models in the workbasket
        in_workbasket = self.filter(workbasket=workbasket)

        # remove matching models from the queryset
        for instance in in_workbasket:
            query &= ~Q(
                **{
                    field: getattr(instance, field)
                    for field in self.model.identifying_fields
                }
            )

        # add latest version of models from the current workbasket
        return self.filter(query) | in_workbasket.filter(successor__isnull=True)

    def approved(self) -> TrackedModelQuerySet:
        """
        Get objects which have been approved/sent-to-cds/published
        """
        return self.filter(
            workbasket__status__in=WorkflowStatus.approved_statuses(),
            workbasket__approver__isnull=False,
        )

    def approved_or_in_workbasket(self, workbasket):
        """
        Get objects which have been approved or are in the specified workbasket.
        """

        return self.filter(
            Q(workbasket=workbasket)
            | Q(
                workbasket__status__in=WorkflowStatus.approved_statuses(),
                workbasket__approver__isnull=False,
            )
        )

    def with_latest_links(self, *lookups) -> TrackedModelQuerySet:
        """
        Annotate each object with the latest data for each related TrackedModel.

        This effectively attaches a dictionary to each model with the data for the
        latest version of any FKs to TrackedModels under the attribute
        _{relation_name}_latest.

        For each FK or 1-2-1 relation found on a TrackedModel the following subquery
        is added as a column to the main query:

        .. code:: SQL

            SELECT Row_to_json({relation_table}) AS "json_data"
              FROM  {relation_table}
             INNER JOIN "common_trackedmodel" U1
                ON {relation_table}."trackedmodel_ptr_id" = U1."id"
             INNER JOIN "workbaskets_workbasket" U2
                ON U1."workbasket_id" = U2."id"
             WHERE {relation_table}.{identifying_field} = {outer_relation_join}.{identifying_field}
               AND U2."status" IN ({approved_statuses})
             ORDER BY {relation_table}."trackedmodel_ptr_id" DESC
             LIMIT 1
        """
        queryset = self.select_related()
        for field, model in self.model.get_relations():
            if lookups and field not in lookups:
                continue
            kwargs = {
                identifying_field: OuterRef(f"{field.name}__{identifying_field}")
                for identifying_field in model.identifying_fields
            }

            latest = (
                model.objects.filter(**kwargs)
                .approved()
                .order_by("-trackedmodel_ptr")
                .annotate(json_data=RowToJson())
                .values("json_data")[:1]
            )

            annotations = {f"_{field.name}_latest": RowToJsonSubquery(latest)}

            queryset = queryset.annotate(**annotations)
        return queryset


class PolymorphicMPTreeQuerySet(TrackedModelQuerySet, MP_NodeQuerySet):
    """
    Combines QuerySets from the TrackedModel system and the MPTT QuerySet from django-treebeard.

    Treebeards QuerySet only overrides the `.delete` method, whereas the Polymorphic QuerySet
    never changes `.delete` so they should work together well.
    """


class PolymorphicMPTreeManager(PolymorphicManager):
    def get_queryset(self):
        """
        The only change the MP_NodeManager from django-treebeard adds to the manager is
        to order the queryset by the path - effectively putting things in tree order.

        This makes it easier to inherit the PolymorphicManager instead which does more work.

        PolymorphicModel also requires the manager to inherit from PolymorphicManager.
        """
        qs = super().get_queryset()
        return qs.order_by("path")


class TimestampedMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class ValidityMixin(models.Model):
    valid_between = DateTimeRangeField()

    class Meta:
        abstract = True


class TrackedModel(PolymorphicModel):
    workbasket = models.ForeignKey(
        "workbaskets.WorkBasket",
        on_delete=models.PROTECT,
        related_name="tracked_models",
    )
    predecessor = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="successor",
        related_query_name="successor",
    )

    update_type = models.PositiveSmallIntegerField(
        choices=validators.UpdateType.choices
    )

    objects = PolymorphicManager.from_queryset(TrackedModelQuerySet)()

    identifying_fields = ("sid",)

    taric_template = None

    def get_taric_template(self) -> str:
        """
        Generate a TARIC XML template name for the given class.

        Any TrackedModel must be representable via a TARIC compatible XML record.
        To facilitate this
        """

        if self.taric_template:
            return self.taric_template
        class_name = self.__class__.__name__

        # replace namesLikeThis to names_Like_This
        name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", class_name)
        # replace names_LIKEthis to names_like_this
        name = re.sub(r"([A-Z]{2,})([a-z0-9_])", r"\1_\2", name).lower()

        template_name = f"taric/{name}.xml"
        try:
            loader.get_template(template_name)
        except loader.TemplateDoesNotExist as e:
            raise loader.TemplateDoesNotExist(
                f"""Taric template does not exist for {class_name}. All classes that \
inherit TrackedModel must either:
    1) Have a matching taric template with a snake_case name matching the class at \
"taric/{{snake_case_class_name}}.xml". In this case it should be: "{template_name}".
    2) A taric_template attribute, pointing to the correct template.
    3) Override the get_taric_template method, returning an existing template."""
            ) from e

        return template_name

    def new_draft(self, workbasket, save: bool = True, **kwargs) -> TrackedModel:
        if hasattr(self, "successor"):
            raise exceptions.AlreadyHasSuccessorError(
                f"Object with PK: {self.pk} already has a successor, can't have multiple successors. "
                f"Use objects.get_latest_version to find the latest instance of this object without a "
                f"successor."
            )
        cls = self.__class__

        new_object_kwargs = {
            field.name: getattr(self, field.name)
            for field in self._meta.fields
            if field.name != "id"
        }

        new_object_kwargs["workbasket"] = workbasket
        new_object_kwargs.setdefault("update_type", validators.UpdateType.UPDATE)
        new_object_kwargs["predecessor"] = self
        new_object_kwargs.pop("polymorphic_ctype")
        new_object_kwargs.pop("trackedmodel_ptr")

        new_object_kwargs.update(kwargs)

        new_object = cls(**new_object_kwargs)

        if save:
            new_object.save()

        return new_object

    def get_versions(self) -> TrackedModelQuerySet:
        query = Q()
        for field in self.identifying_fields:
            query &= Q(**{field: getattr(self, field)})
        return self.__class__.objects.filter(query).order_by("-created_at")

    def get_latest_version(self):
        return self.__class__.objects.get_latest_version(
            **{field: getattr(self, field) for field in self.identifying_fields}
        )

    def validate_workbasket(self):
        pass

    def add_to_workbasket(self, workbasket) -> TrackedModel:
        if workbasket == self.workbasket:
            self.save()
            return self

        return self.new_draft(workbasket=workbasket)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def find_latest_relation(
        self, relation_name: str, model: Type[TrackedModel]
    ) -> TrackedModel:
        """
        Fetch the latest version of an object from the database.

        Objects are often given an FK to a related object at a specific point in time. However
        a new version of the related object may be made at a future date, rendering the current
        key stale (in some cases).

        This method provides a way to fetch the latest version of a related object using just
        the name of the relation and the model type.
        """
        current_instance = getattr(self, relation_name)

        if current_instance is None:
            raise AttributeError(
                f"{relation_name} does not exist on {self.__class__.__name__}"
            )

        kwargs = {
            field: getattr(current_instance, field)
            for field in current_instance.identifying_fields
        }

        return model.objects.approved().get_latest_version(**kwargs)

    def get_latest_relation(
        self, name: str, model: Type[TrackedModel] = None
    ) -> TrackedModel:
        """
        Get the latest version of a related object.

        Similar to find_latest_relation, however checks to see if the data is already cached
        on the instance. This is the case if the instance is built using
        TrackedModelQuerySet.with_current_links.

        If the data is cached then the object is built using this data instead of an extra
        database query.
        """
        relation_data = getattr(self, f"_{name}", None)

        if relation_data is None:
            current_relation = name[:-7]
            return self.find_latest_relation(current_relation, model)

        if "id" not in relation_data:
            relation_data["id"] = relation_data.get("trackedmodel_ptr")

        return model(**relation_data)

    @classmethod
    def get_relations(cls) -> List[Tuple[Field, Type[TrackedModel]]]:
        """
        Find all foreign key and one-to-one relations on an object and return a list containing
        tuples of the field instance and the related model it links to.
        """
        return [
            (f, f.related_model)
            for f in cls._meta.get_fields()
            if (f.many_to_one or f.one_to_one)
            and not f.auto_created
            and f.concrete
            and f.model == cls
            and issubclass(f.related_model, TrackedModel)
        ]

    def __getattr__(self, item: str):
        """
        Add the ability to get the latest instance of a related object through an attribute.

        For example if a model is like so:

        .. code:: python

            class ExampleModel(TrackedModel):
                # must be a TrackedModel
                other_model = models.ForeignKey(OtherModel, on_delete=models.PROTECT)


        The latest version of the relation can be accessed via:

        .. code:: python

            example_model = ExampleModel.objects.first()
            example_model.other_model_latest  # Gets the latest version
        """
        relations = {
            f"{relation.name}_latest": model for relation, model in self.get_relations()
        }
        if item not in relations:
            try:
                return super().__getattr__(item)
            except AttributeError as e:
                raise AttributeError(
                    f"{item} does not exist on {self.__class__.__name__}"
                ) from e
        return self.get_latest_relation(item, model=relations[item])

    def __str__(self):
        return ", ".join(
            f"{field}={getattr(self, field, None)}" for field in self.identifying_fields
        )


class NumericSID(models.PositiveIntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["editable"] = False
        kwargs["validators"] = [validators.NumericSIDValidator()]
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["editable"]
        del kwargs["validators"]
        return name, path, args, kwargs


class SignedIntSID(models.IntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["editable"] = False
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["editable"]
        return name, path, args, kwargs


class ShortDescription(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 500
        kwargs["blank"] = True
        kwargs["null"] = True
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        del kwargs["blank"]
        del kwargs["null"]
        return name, path, args, kwargs


class ApplicabilityCode(models.PositiveSmallIntegerField):
    def __init__(self, *args, **kwargs):
        kwargs["choices"] = validators.ApplicabilityCode.choices
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["choices"]
        return name, path, args, kwargs
