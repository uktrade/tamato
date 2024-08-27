from common.models import TrackedModel
from common.validators import UpdateType
from geo_areas.models import GeographicalArea
from geo_areas.utils import get_all_members_of_geo_groups
from measures import models as measure_models
from typing import List
from typing import Type
from measures.util import diff_components
from workbaskets import models as workbasket_models


def update_measure_components(
        duties: str,
        measure: Type[TrackedModel] = "measure_models.Measure",
        workbasket: Type[TrackedModel] = "workbasket_models.WorkBasket",
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
    workbasket: Type[TrackedModel] = "workbasket_models.WorkBasket",
    measure: Type[TrackedModel] = "measure_models.Measure",
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
    exclusions: List[GeographicalArea],
    workbasket: Type[TrackedModel] = "workbasket_models.WorkBasket",
    measure: Type[TrackedModel] = "measure_models.Measure",
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
