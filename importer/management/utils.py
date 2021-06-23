from typing import Optional

import django.db.transaction
from django.conf import settings
from django.contrib.auth.models import User

from common.models import Transaction
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


def get_author(username: Optional[str] = None) -> User:
    username = username or settings.DATA_IMPORT_USERNAME
    return User.objects.get(username=username)


def start_import_session(title: str, reason: str) -> WorkBasket:
    django.db.transaction.set_autocommit(False)
    print(
        """Django autocommit has now been DISABLED.
            When you are ready to commit your changes,
            you must call importer.management.utils.finalise(...)
            with the returned workbasket.""",
    )

    return WorkBasket.objects.get_or_create(
        title=title,
        reason=reason,
        author=get_author(),
    )


def order_transactions(workbasket: WorkBasket) -> None:
    last_order = (
        Transaction.objects.filter(
            workbasket__status__in=WorkflowStatus.approved_statuses(),
            # Skip first workbasket which is the seed file import
            workbasket__id__gt=WorkBasket.objects.order_by("id").first().id,
        )
        .order_by("order")
        .last()
        .order
    )
    for global_id, txn in enumerate(
        workbasket.transactions.order_by("order"),
        last_order + 1,
    ):
        txn.order = global_id
        txn.save()


def finalise(workbasket: WorkBasket) -> None:
    order_transactions(workbasket)
    workbasket.status = WorkflowStatus.READY_FOR_EXPORT
    workbasket.save()
    django.db.transaction.commit()
