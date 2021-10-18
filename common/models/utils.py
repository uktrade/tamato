from crum import get_current_request
from django.db.models import Subquery
from django.db.models import Value


class DynamicValue(Value):
    def __init__(self, **kwargs) -> None:
        super(Value, self).__init__(**kwargs)

    @property
    def value(self):
        return self.get_value()

    def get_value(self):
        return None


class CurrentWorkBasketId(DynamicValue):
    def get_value(self):
        request = get_current_request()
        if request is None:
            return None

        from workbaskets.models import WorkBasket

        workbasket = WorkBasket.current(request)
        if workbasket:
            return workbasket.id
        return None


class GetCurrentWorkBasketId(Subquery):
    def __init__(self, output_field=None, **extra):
        from workbaskets.models import WorkBasket

        queryset = WorkBasket.objects.filter(pk=CurrentWorkBasketId()).values("id")
        super().__init__(queryset, output_field, **extra)


class CurrentTransactionOrder(DynamicValue):
    def get_value(self):
        request = get_current_request()
        if request is None:
            return 1

        from workbaskets.models import WorkBasket

        transaction = WorkBasket.get_current_transaction(request)
        if transaction:
            return transaction.order
        return 1
