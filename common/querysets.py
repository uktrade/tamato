from datetime import date

from django.db.models import Q
from django.db.models import QuerySet


class ValidityQuerySet(QuerySet):
    def objects_with_validity_field(self):
        return self.model.objects_with_validity_field()

    def not_in_effect(
        self,
        at_date: date,
    ) -> QuerySet:
        return self.objects_with_validity_field().exclude(
            **{f"{self.model.validity_field_name}__contains": at_date},
        )

    def no_longer_in_effect(
        self,
        at_date: date,
    ) -> QuerySet:
        return self.objects_with_validity_field().filter(
            ~Q(**{f"{self.model.validity_field_name}__contains": at_date})
            & ~Q(**{f"{self.model.validity_field_name}__startswith__gt": at_date}),
        )

    def not_yet_in_effect(
        self,
        at_date: date,
    ) -> QuerySet:
        return self.objects_with_validity_field().filter(
            **{f"{self.model.validity_field_name}__startswith__gt": at_date},
        )

    def not_current(
        self,
        asof_transaction=None,
    ) -> QuerySet:
        current = self.approved_up_to_transaction(asof_transaction)

        return self.difference(current)
