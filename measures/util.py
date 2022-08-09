import decimal
from datetime import date
from math import floor
from typing import Type

from common.models import TrackedModel
from common.models.transactions import Transaction
from common.validators import UpdateType
from measures.models import MeasureComponent
from workbaskets.models import WorkBasket


def convert_eur_to_gbp(amount: str, eur_gbp_conversion_rate: float) -> str:
    """Convert EUR amount to GBP and round down to nearest pence."""
    converted_amount = (
        floor(
            int(
                decimal.Decimal(amount)
                * decimal.Decimal(eur_gbp_conversion_rate)
                * 100,
            ),
        )
        / 100
    )
    return f"{converted_amount:.3f}"


def diff_components(
    instance,
    duty_sentence: str,
    start_date: date,
    workbasket: WorkBasket,
    transaction: Type[Transaction],
    component_output: Type[TrackedModel] = MeasureComponent,
    reverse_attribute: str = "component_measure",
):
    """
    Takes a start_date and component_output (MeasureComponent is the default)
    and creates an instance of DutySentenceParser.

    Expects a duty_sentence string and passes this to parser to generate a list
    of new components. Then compares this list with existing components on the
    model instance (either a Measure or a MeasureCondition) and determines
    whether existing components are to be updated, created, or deleted.
    Optionally accepts a Transaction, which should be passed when the method is
    called during the creation of a measure or condition, to minimise the number
    of transactions and avoid business rule violations (e.g.
    ActionRequiresDuty).
    """
    from measures.parsers import DutySentenceParser

    parser = DutySentenceParser.get(
        start_date,
        component_output=component_output,
    )

    new_components = parser.parse(duty_sentence)
    old_components = instance.components.approved_up_to_transaction(
        workbasket.current_transaction,
    )
    new_by_id = {c.duty_expression.id: c for c in new_components}
    old_by_id = {c.duty_expression.id: c for c in old_components}
    all_ids = set(new_by_id.keys()) | set(old_by_id.keys())
    update_transaction = transaction if transaction else None
    for id in all_ids:
        new = new_by_id.get(id)
        old = old_by_id.get(id)
        if new and old:
            # Component is having amount/unit changed – UPDATE it
            new.update_type = UpdateType.UPDATE
            new.version_group = old.version_group
            setattr(new, reverse_attribute, instance)
            if not update_transaction:
                update_transaction = workbasket.new_transaction()
            new.transaction = update_transaction
            new.save()

        elif new:
            # Component exists only in new set - CREATE it
            new.update_type = UpdateType.CREATE
            setattr(new, reverse_attribute, instance)
            new.transaction = (
                transaction if transaction else workbasket.new_transaction()
            )
            new.save()

        elif old:
            # Component exists only in old set – DELETE it
            old = old.new_version(
                workbasket,
                update_type=UpdateType.DELETE,
                transaction=workbasket.new_transaction(),
            )
