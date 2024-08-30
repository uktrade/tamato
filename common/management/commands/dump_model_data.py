from typing import Optional

from django.apps import apps
from django.core import serializers
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db.models import Model
from django.db.models import Q

from common.management.django_filter_parser import DjangoFilterQueryParser


class Command(BaseCommand):
    help = "Dumps data in JSON format for a given model from the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "model",
            metavar="app_label.ModelName",
            help="The name of the model to dump data for.",
        )
        parser.add_argument(
            "--filter",
            default="",
            metavar="field=value[&field2=value|(field3=value&field4=value)]",
            help="One or more field lookup parameters used to filter the model queryset for matching objects. Conditions can be combined using '&' (AND) or '|' (OR) logical operators and nested in parenthesis for order and precedence.",
        )
        parser.add_argument(
            "--slice",
            metavar="offset:limit:step",
            default="",
            help="Limit the queryset to a certain number of results using array-slicing syntax (offset:limit:step).",
        )

    def handle(self, *args, **options):
        try:
            (app_label, model_name) = options["model"].split(".")
            try:
                Model = apps.get_model(app_label, model_name)
            except LookupError as error:
                raise CommandError(str(error))
        except ValueError:
            raise CommandError(
                "Model must be provided in the following format: app_label.ModelName",
            )

        filter_query = DjangoFilterQueryParser().transform(options["filter"])
        slice_indices = self.parse_slice_indices(options["slice"])
        objs_to_serialize = self.get_objects(Model, filter_query, slice_indices)

        self.stdout.write(
            serializers.serialize(
                format="json",
                queryset=objs_to_serialize,
                indent=2,
            ),
        )

    def get_objects(
        self,
        Model: Model,
        filter_query: Q = None,
        slice_indices: tuple[Optional[int], Optional[int], Optional[int]] = None,
    ) -> list[Model]:
        """
        Returns a list of objects to be serialized for `Model`.

        By default, all object records for the specified model are included. Optional filtering and slicing can be applied using `filter_query` and `slice_indices`.
        If an object contains fields that are associated with other models, the related objects will also be included in the returned list.
        """

        queryset = Model.objects.all()

        if filter_query:
            queryset = queryset.filter(filter_query)

        if any(slice_indices):
            offset, limit, step = slice_indices
            queryset = queryset[offset:limit:step]

        objs_to_serialize = []
        seen_objs = set()
        for obj in queryset:
            for field in self.get_relational_fields(Model):
                if field.many_to_one or field.one_to_one:
                    related_obj = getattr(obj, field.name, None)
                    if related_obj:
                        obj_id = (related_obj.__class__.__name__, related_obj.pk)
                        if obj_id not in seen_objs:
                            seen_objs.add(obj_id)
                            objs_to_serialize.append(related_obj)
                elif field.many_to_many:
                    related_objs = getattr(obj, field.get_accessor_name()).all()
                    for related_obj in related_objs:
                        obj_id = (related_obj.__class__.__name__, related_obj.pk)
                        if obj_id not in seen_objs:
                            seen_objs.add(obj_id)
                            objs_to_serialize.append(related_obj)
        objs_to_serialize.extend(queryset)

        return objs_to_serialize

    def get_relational_fields(self, Model):
        """Returns all fields on `Model` with foreign key, one-to-one, or many-
        to-many relationships with other models."""
        return [
            field
            for field in Model._meta.get_fields()
            if (field.many_to_one or field.one_to_one or field.many_to_many)
            and field.concrete
            and not field.auto_created
        ]

    def parse_slice_indices(
        self,
        slice_indices: str,
    ) -> tuple[Optional[int], Optional[int], Optional[int]]:
        """
        Parses a string, `slice_indices`, in the format 'offset:limit:step',
        where each value must be a positive integer if provided.

        Omitted values default to `None`.
        """

        def convert_and_validate(value: str) -> int:
            """
            Converts `value` to an integer.

            Raises a `CommandError` if the string value isn't a positive integer.
            """
            error_message = (
                "Slice indices (offset:limit:step) must be positive integers"
            )
            try:
                value_as_int = int(value)
                if value_as_int <= 0:
                    raise CommandError(error_message)
            except ValueError:
                raise CommandError(error_message)
            return value_as_int

        indices = slice_indices.split(":")
        offset = limit = step = None

        if len(indices) > 3:
            raise CommandError(
                "Slice indices string must be in the format 'offset:limit:step'",
            )

        if len(indices) >= 1 and indices[0]:
            offset = convert_and_validate(indices[0])
        if len(indices) >= 2 and indices[1]:
            limit = convert_and_validate(indices[1])
        if len(indices) == 3 and indices[2]:
            step = convert_and_validate(indices[2])

        return offset, limit, step
