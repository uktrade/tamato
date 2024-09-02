import decimal
from datetime import date
from math import floor
from typing import Type


from common.models import TrackedModel
from common.models.transactions import Transaction
from common.validators import UpdateType
# from measures import models as measure_models
# from workbaskets import models as workbasket_models


import logging
logger = logging.getLogger(__name__)

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
    transaction: Transaction,
    workbasket: "workbasket_models.Workbasket",
    component_output_type: Type = None,
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
    logger.info("DIFF COMPONENTS CALLED")
    from measures.parsers import DutySentenceParser
    from measures.models import MeasureComponent
    # from measures.duty_sentence_parser import DutySentenceParser as LarkDutySentenceParser

    # Setting as a default parameter causes a circular import. To work round it, we set the default to none,
    # Then reassign once we call the function
    component_output_type = MeasureComponent if not component_output_type else component_output_type
    parser = DutySentenceParser.create(
        start_date,
        component_output=component_output_type,
    )
    logger.info(f"DC -  DUTY SENTENCE: {duty_sentence}")
    logger.info(f"DC -  DUTY SENTENCE TYPE: {type(duty_sentence)}")
    new_components = parser.parse(duty_sentence)
    old_components = instance.components.approved_up_to_transaction(
        workbasket.current_transaction,
    )
    logger.info(f"DC -  NEW COMPONENTS: {new_components}")
    logger.info(f"DC -  OLD COMPONENTS: {old_components}")

    new_by_id = {c.duty_expression.id: c for c in new_components}
    old_by_id = {c.duty_expression.id: c for c in old_components}

    logger.info(f"DC -  NEW BY ID: {new_by_id}")
    logger.info(f"DC -  OLD BY ID: {old_by_id}")

    all_ids = set(new_by_id.keys()) | set(old_by_id.keys())

    logger.info(f"DC -  ALL ID: {all_ids}")

    update_transaction = transaction if transaction else None
    for id in all_ids:
        new = new_by_id.get(id)
        old = old_by_id.get(id)
        if new and old:
            # Component is having amount/unit changed – UPDATE it
            logger.info(f"DC IF - NEW: {new}")
            logger.info(f"DC IF - OLD: {old}")
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