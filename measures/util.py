import decimal
from datetime import date
from math import floor

from common.models import TrackedModel
from common.models.transactions import Transaction
from common.validators import UpdateType

from geo_areas.models import GeographicalArea
from geo_areas.utils import get_all_members_of_geo_groups
from measures import models as measure_models
from typing import List
from typing import Type
from workbaskets import models as workbasket_models

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
    workbasket: workbasket_models.WorkBasket,
    transaction: Type[Transaction],
    component_output: Type[TrackedModel] = measure_models.MeasureComponent,
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

    parser = DutySentenceParser.create(
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


def update_measure_components(
    measure: measure_models.Measure,
    duties: str,
    workbasket: workbasket_models.WorkBasket,
):
    """Updates the measure components associated to the measure."""
    diff_components(
        instance=measure,
        duty_sentence=duties if duties else measure.duty_sentence,
        start_date=measure.valid_between.lower,
        workbasket=workbasket,
        transaction=workbasket.current_transaction,
    )


def update_measure_condition_components(
    measure: measure_models.Measure,
    workbasket: workbasket_models.WorkBasket,
):
    """Updates the measure condition components associated to the
    measure."""
    conditions = measure.conditions.current()
    for condition in conditions:
        condition.new_version(
            dependent_measure=measure,
            workbasket=workbasket,
        )


def update_measure_excluded_geographical_areas(
    edited: bool,
    measure: measure_models.Measure,
    exclusions: List[GeographicalArea],
    workbasket: workbasket_models.WorkBasket,
):
    """Updates the excluded geographical areas associated to the measure."""
    existing_exclusions = measure.exclusions.current()

    # Update any exclusions to new measure version
    if not edited:
        for exclusion in existing_exclusions:
            exclusion.new_version(
                modified_measure=measure,
                workbasket=workbasket,
            )
        return

    new_excluded_areas = get_all_members_of_geo_groups(
        validity=measure.valid_between,
        geo_areas=exclusions,
    )

    for geo_area in new_excluded_areas:
        existing_exclusion = existing_exclusions.filter(
            excluded_geographical_area=geo_area,
        ).first()
        if existing_exclusion:
            existing_exclusion.new_version(
                modified_measure=measure,
                workbasket=workbasket,
            )
        else:
            measure_models.MeasureExcludedGeographicalArea.objects.create(
                modified_measure=measure,
                excluded_geographical_area=geo_area,
                update_type=UpdateType.CREATE,
                transaction=workbasket.new_transaction(),
            )

    removed_excluded_areas = {
        e.excluded_geographical_area for e in existing_exclusions
    }.difference(set(exclusions))

    exclusions_to_remove = [
        existing_exclusions.get(excluded_geographical_area__id=geo_area.id)
        for geo_area in removed_excluded_areas
    ]

    for exclusion in exclusions_to_remove:
        exclusion.new_version(
            update_type=UpdateType.DELETE,
            modified_measure=measure,
            workbasket=workbasket,
        )


def update_measure_footnote_associations(measure, workbasket):
    """Updates the footnotes associated to the measure."""
    footnote_associations = (
        measure_models.FootnoteAssociationMeasure.objects.current().filter(
            footnoted_measure__sid=measure.sid,
        )
    )
    for fa in footnote_associations:
        fa.new_version(
            footnoted_measure=measure,
            workbasket=workbasket,
        )
