from datetime import date
from typing import Optional

from django.db import models
from django.db.models import Q
from django.db.models import QuerySet

from common.models import Transaction


class ValidityQuerySet(models.QuerySet):
    def objects_with_validity_field(self):
        return self.model.objects_with_validity_field()

    def get_objects_not_in_effect(
        self,
        asof_date: date,
    ) -> QuerySet:
        return self.objects_with_validity_field().exclude(
            **{f"{self.model.validity_field_name}__contains": asof_date},
        )

    def get_objects_no_longer_in_effect(
        self,
        asof_date: date,
    ) -> QuerySet:
        return self.objects_with_validity_field().filter(
            ~Q(**{f"{self.model.validity_field_name}__contains": asof_date})
            & ~Q(**{f"{self.model.validity_field_name}__startswith__gt": asof_date}),
        )

    def get_objects_not_yet_in_effect(
        self,
        asof_date: date,
    ) -> QuerySet:
        return self.objects_with_validity_field().filter(
            **{f"{self.model.validity_field_name}__startswith__gt": asof_date},
        )

    def get_objects_not_current(
        self,
        asof_transaction: Optional[Transaction] = None,
    ) -> QuerySet:
        current = self.approved_up_to_transaction(asof_transaction)

        return self.difference(current)
